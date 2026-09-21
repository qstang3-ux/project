import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str, secret: str) -> str:
    if not secret:
        raise ValueError("MODEL_SECRET_KEY is required to persist API keys")
    return _fernet(secret).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str, secret: str) -> str:
    try:
        return _fernet(secret).decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt model API key") from exc


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    suffix = value[-4:] if len(value) >= 4 else value
    return f"****{suffix}"
