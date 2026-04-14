from fastapi import FastAPI

from app.api.routes.products import router as products_router
from app.api.routes.users import router as users_router

app = FastAPI(title="Kraftista Backend", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(users_router, prefix="/api")
app.include_router(products_router, prefix="/api")
