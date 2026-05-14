"""JWT creation and FastAPI dependencies for authenticated routes."""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.hashing import verify_password
from backend.models import User
from backend.schemas import TokenPayload

SECRET_KEY = os.environ.get(
    "CERTVERIFY_SECRET_KEY",
    "change-me-in-production-use-a-long-random-secret",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Return the user if email/password are valid, else None."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Encode a JWT with subject (user id), expiry, and optional extra claims (e.g. role)."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT; raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        exp = payload.get("exp")
        role = payload.get("role")
        return TokenPayload(
            sub=str(sub),
            exp=int(exp) if exp is not None else None,
            role=str(role) if role is not None else None,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> User:
    """Dependency: require Bearer token and return the current user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = decode_token(token)
    user_id = int(payload.sub)  # type: ignore[arg-type]
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_current_user_optional(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> Optional[User]:
    """Dependency: return user if valid token present, else None."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = int(payload.sub)  # type: ignore[arg-type]
        return db.query(User).filter(User.id == user_id).first()
    except HTTPException:
        return None
