"""SQLAlchemy ORM models for CertVerify."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class UserRole(str, enum.Enum):
    INSTITUTION = "institution"
    VERIFIER = "verifier"


class CertificateStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=UserRole.INSTITUTION.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    certificates_issued: Mapped[List["Certificate"]] = relationship(
        "Certificate",
        back_populates="issued_by",
        foreign_keys="Certificate.issued_by_user_id",
    )


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    cert_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rsa_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    public_key_pem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qr_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CertificateStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    issued_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    issued_by: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="certificates_issued",
        foreign_keys=[issued_by_user_id],
    )
    verification_logs: Mapped[List["VerificationLog"]] = relationship(
        "VerificationLog",
        back_populates="certificate",
        cascade="all, delete-orphan",
    )


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    certificate_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result: Mapped[str] = mapped_column(String(64), nullable=False)
    forgery_label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    forgery_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    verifier_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    certificate: Mapped["Certificate"] = relationship(
        "Certificate",
        back_populates="verification_logs",
    )
    verifier: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[verifier_user_id],
    )