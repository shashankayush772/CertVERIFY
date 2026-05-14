"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Users ---


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(..., min_length=1, max_length=32)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    role: Optional[str] = None


# --- Certificates ---


class CertificateBase(BaseModel):
    student_name: str = Field(max_length=255)
    degree: str = Field(max_length=255)
    institution_name: str = Field(max_length=255)
    issue_date: datetime


class CertificateCreate(CertificateBase):
    file_path: str = Field(max_length=512)
    cert_hash: str = Field(max_length=128)
    rsa_signature: Optional[str] = None
    public_key_pem: Optional[str] = None
    qr_path: Optional[str] = Field(default=None, max_length=512)
    status: str = Field(default="active", max_length=32)


class CertificateRead(CertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    cert_hash: str
    rsa_signature: Optional[str]
    public_key_pem: Optional[str]
    qr_path: Optional[str]
    status: str
    created_at: datetime


class CertificateIssueResponse(CertificateRead):
    """Response after issuing a certificate (includes aliases and QR payload for the client)."""

    cert_id: int
    qr_image_base64: str = Field(description="PNG bytes, base64-encoded (no data URL prefix)")


class CertificateMyItem(BaseModel):
    """One row for GET /certificates/my."""

    id: int
    student_name: str
    degree: str
    institution_name: str
    issue_date: datetime
    status: str
    verification_count: int
    qr_download_url: Optional[str] = None


class CertificatesMyResponse(BaseModel):
    certificates: List[CertificateMyItem]


class VerifyPublicResponse(BaseModel):
    student_name: str
    degree: str
    institution_name: str
    issue_date: datetime
    status: str
    cert_hash: str


class VerifyUploadResponse(BaseModel):
    verdict: str
    reason: Optional[str] = None
    forgery_label: Optional[str] = None
    forgery_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    student_name: Optional[str] = None
    degree: Optional[str] = None
    institution_name: Optional[str] = None
    issue_date: Optional[str] = None
    cert_hash: Optional[str] = None


class VerificationHistoryItem(BaseModel):
    """One row for GET /verifications/my."""

    id: int
    certificate_id: int
    student_name: str
    result: str
    verified_at: datetime


class VerificationsMyResponse(BaseModel):
    verifications: List[VerificationHistoryItem]


# --- Verification logs ---


class VerificationLogBase(BaseModel):
    result: str = Field(max_length=64)
    forgery_label: Optional[str] = Field(default=None, max_length=64)
    forgery_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ip_address: Optional[str] = Field(default=None, max_length=45)


class VerificationLogCreate(VerificationLogBase):
    certificate_id: int


class VerificationLogRead(VerificationLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    certificate_id: int
    verified_at: datetime


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    service: str
