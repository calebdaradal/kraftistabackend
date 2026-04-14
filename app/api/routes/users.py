import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.users import create_user, get_user_or_404, list_users, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def create_user_endpoint(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    user = create_user(db, payload)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(user_id: uuid.UUID, db: Session = Depends(get_db)) -> UserRead:
    user = get_user_or_404(db, user_id)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user_endpoint(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db)) -> UserRead:
    user = get_user_or_404(db, user_id)
    updated = update_user(db, user, payload)
    return UserRead.model_validate(updated)


@router.get("", response_model=list[UserRead])
def list_users_endpoint(
    email: str | None = Query(default=None),
    role: UserRole | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    users = list_users(db, email=email, role=role.value if role else None)
    return [UserRead.model_validate(user) for user in users]
