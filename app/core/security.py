import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def _bcrypt_safe_secret(password: str) -> str:
    # bcrypt has a 72-byte limit; pre-hash long inputs to keep behavior stable.
    secret_bytes = password.encode("utf-8")
    if len(secret_bytes) <= 72:
        return password
    return hashlib.sha256(secret_bytes).hexdigest()


def hash_password(password: str) -> str:
    safe_password = _bcrypt_safe_secret(password).encode("utf-8")
    return bcrypt.hashpw(safe_password, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    safe_password = _bcrypt_safe_secret(password).encode("utf-8")
    return bcrypt.checkpw(safe_password, password_hash.encode("utf-8"))


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_exp_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token.") from exc
    subject = payload.get("sub")
    if not subject:
        raise ValueError("Token missing subject.")
    return str(subject)
