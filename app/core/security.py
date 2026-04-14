import hashlib
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _bcrypt_safe_secret(password: str) -> str:
    # bcrypt has a 72-byte limit; pre-hash long inputs to keep behavior stable.
    secret_bytes = password.encode("utf-8")
    if len(secret_bytes) <= 72:
        return password
    return hashlib.sha256(secret_bytes).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_bcrypt_safe_secret(password))


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(_bcrypt_safe_secret(password), password_hash)


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
