import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


def _apply_user_filters(query: Select[tuple[User]], email: str | None, role: str | None) -> Select[tuple[User]]:
    if email:
        query = query.where(User.email == email)
    if role:
        query = query.where(User.role == role)
    return query


def create_user(db: Session, payload: UserCreate) -> User:
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

    address = payload.address
    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        phone=payload.phone,
        is_active=payload.is_active,
        address_street=address.street if address else None,
        address_city=address.city if address else None,
        address_state=address.state if address else None,
        address_zip_code=address.zip_code if address else None,
        address_country=address.country if address else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    update_data = payload.model_dump(exclude_unset=True)
    address = update_data.pop("address", None)

    for key, value in update_data.items():
        setattr(user, key, value)

    if address is not None:
        user.address_street = address.get("street")
        user.address_city = address.get("city")
        user.address_state = address.get("state")
        user.address_zip_code = address.get("zip_code")
        user.address_country = address.get("country")

    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, email: str | None, role: str | None) -> list[User]:
    query = select(User).order_by(User.created_at.desc())
    query = _apply_user_filters(query, email, role)
    return list(db.scalars(query).all())


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def ensure_admin_user(db: Session, email: str, password: str, full_name: str) -> User:
    existing = get_user_by_email(db, email)
    if existing is not None:
        return existing
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRole.admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
