"""SQLAlchemy engine, session factory, and database utilities for CertVerify."""

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Store SQLite file next to backend package by default
_BACKEND_DIR = Path(__file__).resolve().parent
_DEFAULT_DB_PATH = _BACKEND_DIR / "certverify.db"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_DB_PATH}",
)

# SQLite needs check_same_thread=False when used with FastAPI async workers
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.environ.get("SQL_ECHO", "").lower() in ("1", "true", "yes"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_db():
    """Yield a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_migrate_certificates() -> None:
    """Upgrade legacy SQLite certificates rows/columns for Step 2 schema."""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='certificates'")
        ).fetchone()
        if exists is None:
            return
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(certificates)"))}
        if "institution_name" not in cols:
            conn.execute(
                text("ALTER TABLE certificates ADD COLUMN institution_name TEXT DEFAULT ''")
            )
            conn.execute(
                text("UPDATE certificates SET institution_name = '' WHERE institution_name IS NULL")
            )
        if "public_key_pem" not in cols:
            conn.execute(text("ALTER TABLE certificates ADD COLUMN public_key_pem TEXT"))
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(certificates)"))}
        if "institution_id" in cols:
            try:
                conn.execute(text("ALTER TABLE certificates DROP COLUMN institution_id"))
            except Exception:
                pass


def _sqlite_migrate_roles_and_fks() -> None:
    """Add issuer/verifier FK columns and normalize legacy user roles."""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        user_tbl = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'")
        ).fetchone()
        if user_tbl is not None:
            conn.execute(
                text(
                    "UPDATE users SET role = 'institution' "
                    "WHERE role IN ('viewer', 'admin', 'issuer')"
                )
            )

        cert_tbl = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='certificates'")
        ).fetchone()
        if cert_tbl is not None:
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(certificates)"))}
            if "issued_by_user_id" not in cols:
                conn.execute(
                    text("ALTER TABLE certificates ADD COLUMN issued_by_user_id INTEGER")
                )

        log_tbl = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='verification_logs'")
        ).fetchone()
        if log_tbl is not None:
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(verification_logs)"))}
            if "verifier_user_id" not in cols:
                conn.execute(
                    text("ALTER TABLE verification_logs ADD COLUMN verifier_user_id INTEGER")
                )


def _sqlite_migrate_blockchain() -> None:
    """Add blockchain_tx_hash column to certificates table if missing."""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        cert_tbl = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='certificates'")
        ).fetchone()
        if cert_tbl is None:
            return
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(certificates)"))}
        if "blockchain_tx_hash" not in cols:
            conn.execute(
                text("ALTER TABLE certificates ADD COLUMN blockchain_tx_hash VARCHAR")
            )
            print("[DB] Added blockchain_tx_hash column to certificates")


def init_db() -> None:
    """Create all tables defined on Base.metadata and run lightweight SQLite upgrades."""
    from backend import models  # noqa: F401 — register models

    Base.metadata.create_all(bind=engine)
    _sqlite_migrate_certificates()
    _sqlite_migrate_roles_and_fks()
    _sqlite_migrate_blockchain()