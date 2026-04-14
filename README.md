# Kraftista FastAPI Backend

Simple FastAPI backend for users, products, auth, cart, and orders using Supabase Postgres.

## 1) Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy env file and update values:

```bash
copy .env.example .env
```

## 2) Run Migrations

```bash
alembic upgrade head
```

## 3) Start API

```bash
uvicorn app.main:app --reload
```

Render start command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 4) Endpoints

- Health: `GET /health`
- Users:
  - `POST /api/users`
  - `GET /api/users/{user_id}`
  - `PATCH /api/users/{user_id}`
  - `GET /api/users?email=&role=`
- Auth:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
- Products:
  - `POST /api/products`
  - `GET /api/products/{product_id}`
  - `PATCH /api/products/{product_id}`
  - `DELETE /api/products/{product_id}` (soft delete via `active=false`)
  - `GET /api/products?category=&active=&q=`
- Customer:
  - `GET /api/customer/cart`
  - `POST /api/customer/cart/items`
  - `DELETE /api/customer/cart/items/{item_id}`
  - `POST /api/customer/checkout`
  - `GET /api/customer/orders`

## 5) Example payloads

Create user:

```json
{
  "email": "jane@example.com",
  "password": "secret123",
  "full_name": "Jane Doe",
  "role": "customer",
  "phone": "+15550001234",
  "address": {
    "street": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "country": "USA"
  }
}
```

Login:

```json
{
  "email": "admin@example.com",
  "password": "strong-password"
}
```

Create product:

```json
{
  "name": "Handmade Ceramic Mug",
  "sku": "MUG-001",
  "price": 24.99,
  "stock_count": 20,
  "in_stock": true,
  "active": true,
  "tags": ["ceramic", "kitchen"],
  "materials": ["clay", "glaze"]
}
```

## 6) Security Notes

- Transport security should use HTTPS/TLS in production (Render handles this at the edge).
- Passwords are stored hashed (`bcrypt` via passlib), not plaintext.
- Use a strong `JWT_SECRET_KEY` in environment variables.
- Do not commit `.env` or secrets.

## 7) Admin Bootstrap

If `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set, the app creates the first admin account at startup if it does not exist.

## 8) Render + Supabase

- Use Supabase pooler URI (`port 6543`) with `sslmode=require`.
- Render Build Command:

```bash
pip install -r requirements.txt
```

- Render Start Command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
