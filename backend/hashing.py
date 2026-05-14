"""Password hashing (bcrypt) and certificate integrity (SHA-256, RSA)."""

import base64
import hashlib
from typing import Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric import utils as asym_utils
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def compute_file_hash(file_bytes: bytes) -> str:
    """Return lowercase SHA-256 hex digest of the file contents."""
    return hashlib.sha256(file_bytes).hexdigest()


def generate_rsa_keypair() -> Tuple[str, str]:
    """
    Generate a new RSA keypair.

    Returns (private_key_pem, public_key_pem) as UTF-8 PEM strings.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv_pem.decode("utf-8"), pub_pem.decode("utf-8")


def sign_hash(hash_hex: str, private_key_pem: str) -> str:
    """
    Sign a SHA-256 digest (64 hex characters) with the private key.

    Uses PKCS1v15 padding with a pre-hashed SHA-256 message.
    Returns base64-encoded signature.
    """
    digest = bytes.fromhex(hash_hex)
    if len(digest) != hashlib.sha256().digest_size:
        raise ValueError("hash_hex must represent a 32-byte SHA-256 digest (64 hex chars)")

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError("private_key_pem must decode to an RSA private key")

    signature = private_key.sign(
        digest,
        padding.PKCS1v15(),
        asym_utils.Prehashed(hashes.SHA256()),
    )
    return base64.b64encode(signature).decode("ascii")


def verify_signature(hash_hex: str, signature_b64: str, public_key_pem: str) -> bool:
    """
    Verify that signature_b64 is a valid RSA signature over the SHA-256 digest hash_hex.

    Returns False on any failure (wrong key, bad encoding, invalid signature).
    """
    try:
        digest = bytes.fromhex(hash_hex)
        if len(digest) != hashlib.sha256().digest_size:
            return False
        signature = base64.b64decode(signature_b64)
    except (ValueError, TypeError):
        return False

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, rsa.RSAPublicKey):
            return False
        public_key.verify(
            signature,
            digest,
            padding.PKCS1v15(),
            asym_utils.Prehashed(hashes.SHA256()),
        )
        return True
    except Exception:
        return False
