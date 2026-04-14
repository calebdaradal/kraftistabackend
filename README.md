# Kraftista FastAPI Backend

Simple FastAPI backend for `users` and `products` using Supabase Postgres.

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
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 4) Endpoints

- Health: `GET /health`
- Users:
  - `POST /api/users`
  - `GET /api/users/{user_id}`
  - `PATCH /api/users/{user_id}`
  - `GET /api/users?email=&role=`
- Products:
  - `POST /api/products`
  - `GET /api/products/{product_id}`
  - `PATCH /api/products/{product_id}`
  - `DELETE /api/products/{product_id}` (soft delete via `active=false`)
  - `GET /api/products?category=&active=&q=`

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
