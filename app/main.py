from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.customer import router as customer_router
from app.api.routes.orders import router as orders_router
from app.api.routes.products import router as products_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.users import ensure_admin_user

app = FastAPI(title="Kraftista Backend", version="0.1.0")
settings = get_settings()

allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(users_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(customer_router, prefix="/api")
app.include_router(orders_router, prefix="/api")


@app.on_event("startup")
def bootstrap_admin_user() -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    with SessionLocal() as db:
        ensure_admin_user(
            db=db,
            email=settings.admin_email,
            password=settings.admin_password,
            full_name=settings.admin_name,
        )
