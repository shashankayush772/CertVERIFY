"""Generate QR codes for certificate verification payloads."""

from __future__ import annotations

import os

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def _backend_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def generate_qr(cert_id: int, base_url: str) -> str:
    """
    Generate a QR code PNG that points to ``{base_url}/verify/{cert_id}``.

    Saves to ``backend/uploads/qr_{cert_id}.png`` and returns the absolute file path
    (normalized for the current OS, e.g. Windows).
    """
    uploads_dir = os.path.join(_backend_dir(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    filename = f"qr_{cert_id}.png"
    out_path = os.path.join(uploads_dir, filename)
    verify_url = base_url.rstrip("/") + f"/verify/{cert_id}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)

    return os.path.abspath(out_path)


def generate_qr_png(data: str, output_path: str | os.PathLike[str], box_size: int = 10, border: int = 2) -> str:
    """
    Encode ``data`` as a QR code and save as PNG.

    Creates parent directories if needed. Returns the absolute path as a string.
    """
    out = os.fspath(output_path)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out)
    return os.path.abspath(out)


def qr_data_for_certificate(cert_id: int, cert_hash: str, base_url: str = "https://certverify.local") -> str:
    """Build a verification URL or payload string stored in the QR code."""
    base = base_url.rstrip("/")
    return f"{base}/verify?id={cert_id}&h={cert_hash}"
