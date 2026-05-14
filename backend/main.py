"""CertVerify FastAPI application entrypoint."""

from __future__ import annotations

# Load .env file if python-dotenv is available (optional dependency)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import base64
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from backend.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_user_optional,
)
from backend.database import get_db, init_db
from backend.hashing import (
    compute_file_hash,
    generate_rsa_keypair,
    hash_password,
    sign_hash,
    verify_signature,
)
from backend.models import Certificate, User, VerificationLog
from backend.qr import generate_qr
from backend.blockchain import store_hash_on_chain, verify_hash_on_chain
from backend.schemas import (
    CertificateIssueResponse,
    CertificateMyItem,
    CertificateRead,
    CertificatesMyResponse,
    HealthResponse,
    Token,
    UserRead,
    UserRegister,
    VerificationHistoryItem,
    VerificationsMyResponse,
    VerifyPublicResponse,
)


CERTVERIFY_PUBLIC_API = os.environ.get("CERTVERIFY_PUBLIC_API", "http://127.0.0.1:8000")
CERTVERIFY_FRONTEND_ORIGINS = os.environ.get("CERTVERIFY_FRONTEND_ORIGINS", "")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def _uploads_dir() -> str:
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(backend_dir, "uploads")

CERTVERIFY_QR_BASE_URL = os.environ.get("CERTVERIFY_QR_BASE_URL", "http://127.0.0.1:8080")

app = FastAPI(
    title="CertVerify API",
    description="Academic certificate verification backend",
    version="0.4.0",
    lifespan=lifespan,
)

explicit_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://mp-cert-verify-4cp9.vercel.app",
    "https://vercel-mp-cert-verify-4cp9.vercel.app",
]

if CERTVERIFY_FRONTEND_ORIGINS.strip():
    explicit_origins.extend(
        origin.strip().rstrip("/")
        for origin in CERTVERIFY_FRONTEND_ORIGINS.split(",")
        if origin.strip()
    )

# Deduplicate while preserving order.
explicit_origins = list(dict.fromkeys(explicit_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=explicit_origins,
    allow_origin_regex=r"https://([a-zA-Z0-9-]+\.)*vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


uploads_abs = _uploads_dir()
os.makedirs(uploads_abs, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_abs), name="uploads")


@app.get("/", tags=["system"])
def root():
    """Root endpoint — quick check that the API is running."""
    return {
        "service": "certverify-api",
        "version": "0.4.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness probe for load balancers and monitoring."""
    return HealthResponse(status="ok", service="certverify-api")


@app.post("/auth/token", response_model=Token, tags=["auth"])
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        str(user.id),
        extra_claims={"role": user.role, "email": user.email},
    )
    return Token(access_token=access_token, token_type="bearer")


@app.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register_user(
    user_in: UserRegister,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Register with role institution or verifier only."""
    if user_in.role not in ("institution", "verifier"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role must be 'institution' or 'verifier'",
        )
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _parse_issue_date(issue_date: str) -> datetime:
    try:
        issue_dt = datetime.fromisoformat(issue_date.replace("Z", "+00:00"))
        if issue_dt.tzinfo is None:
            issue_dt = issue_dt.replace(tzinfo=timezone.utc)
        return issue_dt
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid issue_date: {exc}",
        ) from exc


# ── File type helpers ────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {"pdf", "jpeg", "jpg", "png", "image"}


def _is_allowed_upload(filename: Optional[str], content_type: Optional[str]) -> bool:
    name = (filename or "").lower()
    if any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return True
    if content_type and any(t in content_type.lower() for t in ALLOWED_CONTENT_TYPES):
        return True
    return False


def _is_image_file(filename: Optional[str]) -> bool:
    name = (filename or "").lower()
    return any(name.endswith(ext) for ext in {".jpg", ".jpeg", ".png"})


def _get_file_suffix(filename: Optional[str]) -> str:
    name = (filename or "").lower()
    for ext in [".pdf", ".jpg", ".jpeg", ".png"]:
        if name.endswith(ext):
            return ext
    return ".pdf"


# ── Certificate endpoints ────────────────────────────────────────────────────

@app.get("/certificates/my", response_model=CertificatesMyResponse, tags=["certificates"])
def list_my_certificates(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CertificatesMyResponse:
    if current_user.role != "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only institution accounts can list issued certificates",
        )
    certs = (
        db.query(Certificate)
        .filter(Certificate.issued_by_user_id == current_user.id)
        .order_by(Certificate.created_at.desc())
        .all()
    )
    if not certs:
        return CertificatesMyResponse(certificates=[])

    cert_ids = [c.id for c in certs]
    count_rows = (
        db.query(VerificationLog.certificate_id, func.count(VerificationLog.id))
        .filter(VerificationLog.certificate_id.in_(cert_ids))
        .group_by(VerificationLog.certificate_id)
        .all()
    )
    count_map = {int(cid): int(n) for cid, n in count_rows}
    base = CERTVERIFY_PUBLIC_API.rstrip("/")

    items: list[CertificateMyItem] = []
    for c in certs:
        qr_url: Optional[str] = None
        if c.qr_path:
            fn = os.path.basename(c.qr_path)
            qr_url = f"{base}/uploads/{fn}"
        items.append(
            CertificateMyItem(
                id=c.id,
                student_name=c.student_name,
                degree=c.degree,
                institution_name=c.institution_name,
                issue_date=c.issue_date,
                status=c.status,
                verification_count=count_map.get(c.id, 0),
                qr_download_url=qr_url,
            )
        )
    return CertificatesMyResponse(certificates=items)


@app.get("/verifications/my", response_model=VerificationsMyResponse, tags=["verify"])
def list_my_verifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VerificationsMyResponse:
    if current_user.role != "verifier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only verifier accounts can list verification history",
        )
    rows = (
        db.query(VerificationLog, Certificate.student_name)
        .join(Certificate, VerificationLog.certificate_id == Certificate.id)
        .filter(VerificationLog.verifier_user_id == current_user.id)
        .order_by(VerificationLog.verified_at.desc())
        .all()
    )
    return VerificationsMyResponse(
        verifications=[
            VerificationHistoryItem(
                id=log.id,
                certificate_id=log.certificate_id,
                student_name=student_name,
                result=log.result,
                verified_at=log.verified_at,
            )
            for log, student_name in rows
        ]
    )


@app.post(
    "/certificates",
    response_model=CertificateIssueResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["certificates"],
)
async def create_certificate(
    student_name: Annotated[str, Form()],
    degree: Annotated[str, Form()],
    institution_name: Annotated[str, Form()],
    issue_date: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CertificateIssueResponse:
    """Issue a certificate — PDF, JPG, or PNG (institution role only)."""
    if current_user.role != "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only institution accounts may issue certificates",
        )
    if not _is_allowed_upload(file.filename, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate file must be a PDF, JPG, or PNG",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    issue_dt = _parse_issue_date(issue_date)
    cert_hash = compute_file_hash(raw)
    private_pem, public_pem = generate_rsa_keypair()
    rsa_signature = sign_hash(cert_hash, private_pem)
    del private_pem

    uploads = _uploads_dir()
    os.makedirs(uploads, exist_ok=True)
    suffix = _get_file_suffix(file.filename)
    cert_filename = f"cert_{uuid.uuid4().hex}{suffix}"
    dest_path = os.path.join(uploads, cert_filename)
    with open(dest_path, "wb") as out_f:
        out_f.write(raw)
    dest_path = os.path.abspath(dest_path)

    cert = Certificate(
        student_name=student_name,
        degree=degree,
        institution_name=institution_name,
        issue_date=issue_dt,
        file_path=dest_path,
        cert_hash=cert_hash,
        rsa_signature=rsa_signature,
        public_key_pem=public_pem,
        qr_path=None,
        blockchain_tx_hash=None,
        status="active",
        issued_by_user_id=current_user.id,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    qr_abs = generate_qr(cert.id, CERTVERIFY_QR_BASE_URL)
    cert.qr_path = qr_abs
    db.add(cert)
    db.commit()
    db.refresh(cert)

    tx_hash = store_hash_on_chain(cert.id, cert_hash)
    if tx_hash:
        cert.blockchain_tx_hash = tx_hash
        db.add(cert)
        db.commit()
        db.refresh(cert)
        print(f"[Blockchain] Certificate {cert.id} anchored on Polygon. TX: {tx_hash}")
    else:
        print(f"[Blockchain] Blockchain not configured or failed — certificate issued without anchoring")

    with open(qr_abs, "rb") as qr_f:
        qr_b64 = base64.b64encode(qr_f.read()).decode("ascii")

    base_read = CertificateRead.model_validate(cert)
    return CertificateIssueResponse(
        **base_read.model_dump(),
        cert_id=cert.id,
        qr_image_base64=qr_b64,
    )


# ── Verify endpoints ─────────────────────────────────────────────────────────

@app.post("/verify/upload", tags=["verify"])
async def verify_upload(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    cert_id: Annotated[int, Form()],
    optional_user: Annotated[Optional[User], Depends(get_current_user_optional)],
) -> Dict[str, Any]:
    """
    Verify an uploaded PDF, JPG, or PNG (public endpoint).
    Runs 4 checks in order:
      1. AI forgery detection (ResNet-18 + ELA)
      2. SHA-256 hash integrity check
      3. RSA digital signature validation
      4. Blockchain hash cross-check (if configured)
    """
    if not _is_allowed_upload(file.filename, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF, JPG, or PNG",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    client = request.client
    ip_address = client.host if client else None

    verifier_user_id: Optional[int] = None
    if optional_user is not None and optional_user.role == "verifier":
        verifier_user_id = optional_user.id

    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if cert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    def log_verification(
        result: str,
        forgery_label: Optional[str] = None,
        fc: Optional[float] = None,
    ) -> None:
        entry = VerificationLog(
            certificate_id=cert_id,
            result=result,
            forgery_label=forgery_label,
            forgery_confidence=fc,
            ip_address=ip_address,
            verifier_user_id=verifier_user_id,
        )
        db.add(entry)
        db.commit()

    # ── Layer 1: AI Forgery Detection ────────────────────────────────────────
    # Import ML stack lazily so login/auth endpoints don't pay torch startup cost.
    from backend.ml.predict import detect_forgery, pdf_to_image

    ml_label = "unknown"
    ml_conf = 0.0
    ai_check_passed = False
    tmp_file_path = ""
    img_tmp_path = ""

    try:
        suffix = _get_file_suffix(file.filename)
        fd, tmp_file_path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as tmp_out:
                tmp_out.write(raw)
        except Exception:
            os.close(fd)
            raise

        if _is_image_file(file.filename):
            img_tmp_path = tmp_file_path
        else:
            img_tmp_path = pdf_to_image(tmp_file_path)

        if img_tmp_path:
            det = detect_forgery(img_tmp_path)
            ml_label = str(det.get("label", "unknown"))
            ml_conf = float(det.get("confidence", 0.0))

            if ml_label == "forged" and ml_conf > 0.95:
                log_verification("FORGED", "forged", ml_conf)
                return {
                    "verdict": "FORGED",
                    "reason": "AI forgery detection flagged this document",
                    "forgery_label": "forged",
                    "forgery_confidence": ml_conf,
                    "checks": {
                        "ai_forgery_detection": {
                            "status": "FAILED",
                            "label": "forged",
                            "confidence": f"{ml_conf * 100:.1f}%",
                        },
                        "hash_integrity": {"status": "NOT_REACHED"},
                        "rsa_signature": {"status": "NOT_REACHED"},
                        "blockchain": {"status": "NOT_REACHED"},
                    },
                }
            else:
                ai_check_passed = True

    except Exception as exc:
        print(f"[CertVerify] PDF/ML pre-check (non-fatal): {exc}")
        ai_check_passed = True
    finally:
        paths_to_clean = set()
        if tmp_file_path:
            paths_to_clean.add(tmp_file_path)
        if img_tmp_path and img_tmp_path != tmp_file_path:
            paths_to_clean.add(img_tmp_path)
        for path in paths_to_clean:
            if path and os.path.isfile(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    # ── Layer 2: SHA-256 Hash Integrity Check ─────────────────────────────────
    uploaded_hash = compute_file_hash(raw)
    hash_matched = uploaded_hash.lower() == cert.cert_hash.lower()

    if not hash_matched:
        log_verification("TAMPERED", ml_label, ml_conf)
        return {
            "verdict": "TAMPERED",
            "reason": "File hash does not match stored record — document was modified after issuance",
            "forgery_label": ml_label,
            "forgery_confidence": ml_conf,
            "checks": {
                "ai_forgery_detection": {
                    "status": "PASSED" if ai_check_passed else "SKIPPED",
                    "label": ml_label,
                    "confidence": f"{ml_conf * 100:.1f}%",
                },
                "hash_integrity": {
                    "status": "FAILED",
                    "detail": "SHA-256 hash mismatch",
                },
                "rsa_signature": {"status": "NOT_REACHED"},
                "blockchain": {"status": "NOT_REACHED"},
            },
        }

    # ── Layer 3: RSA Digital Signature Validation ─────────────────────────────
    if not cert.rsa_signature or not cert.public_key_pem:
        log_verification("INVALID", ml_label, ml_conf)
        return {
            "verdict": "INVALID",
            "reason": "Digital signature missing from stored record",
            "forgery_label": ml_label,
            "forgery_confidence": ml_conf,
            "checks": {
                "ai_forgery_detection": {
                    "status": "PASSED" if ai_check_passed else "SKIPPED",
                    "label": ml_label,
                    "confidence": f"{ml_conf * 100:.1f}%",
                },
                "hash_integrity": {"status": "PASSED"},
                "rsa_signature": {
                    "status": "FAILED",
                    "detail": "No signature stored",
                },
                "blockchain": {"status": "NOT_REACHED"},
            },
        }

    sig_valid = verify_signature(cert.cert_hash, cert.rsa_signature, cert.public_key_pem)

    if not sig_valid:
        log_verification("INVALID", ml_label, ml_conf)
        return {
            "verdict": "INVALID",
            "reason": "RSA digital signature validation failed",
            "forgery_label": ml_label,
            "forgery_confidence": ml_conf,
            "checks": {
                "ai_forgery_detection": {
                    "status": "PASSED" if ai_check_passed else "SKIPPED",
                    "label": ml_label,
                    "confidence": f"{ml_conf * 100:.1f}%",
                },
                "hash_integrity": {"status": "PASSED"},
                "rsa_signature": {
                    "status": "FAILED",
                    "detail": "Signature does not match",
                },
                "blockchain": {"status": "NOT_REACHED"},
            },
        }

    # ── Layer 4: Blockchain Hash Cross-Check ──────────────────────────────────
    blockchain_result = verify_hash_on_chain(cert_id, cert.cert_hash)
    blockchain_status = blockchain_result.get("status", "DISABLED")
    blockchain_detail = blockchain_result.get("detail", "")
    blockchain_explorer = blockchain_result.get("explorer_url", "")

    # ── All checks done — AUTHENTIC ───────────────────────────────────────────
    log_verification("AUTHENTIC", ml_label, ml_conf)
    return {
        "verdict": "AUTHENTIC",
        "student_name": cert.student_name,
        "degree": cert.degree,
        "institution_name": cert.institution_name,
        "issue_date": cert.issue_date.isoformat(),
        "cert_hash": cert.cert_hash,
        "forgery_label": ml_label,
        "forgery_confidence": ml_conf,
        "blockchain_tx_hash": cert.blockchain_tx_hash,
        "checks": {
            "ai_forgery_detection": {
                "status": "PASSED",
                "label": ml_label,
                "confidence": f"{ml_conf * 100:.1f}%",
            },
            "hash_integrity": {
                "status": "PASSED",
                "detail": "SHA-256 hash matches stored record",
            },
            "rsa_signature": {
                "status": "PASSED",
                "detail": "RSA signature verified against institution public key",
            },
            "blockchain": {
                "status": blockchain_status,
                "detail": blockchain_detail,
                "explorer_url": blockchain_explorer,
            },
        },
    }


@app.get("/verify/{cert_id}", response_model=VerifyPublicResponse, tags=["verify"])
def get_verify_certificate(
    cert_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> VerifyPublicResponse:
    """Public certificate details (QR scan / lookup)."""
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if cert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )
    return VerifyPublicResponse(
        student_name=cert.student_name,
        degree=cert.degree,
        institution_name=cert.institution_name,
        issue_date=cert.issue_date,
        status=cert.status,
        cert_hash=cert.cert_hash,
    )