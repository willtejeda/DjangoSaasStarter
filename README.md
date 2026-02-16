# Django + Supabase + Clerk + Preact SaaS Starter

Production-minded SaaS starter with:
- Django for ORM and REST API
- Supabase for managed Postgres and optional RLS client access
- Clerk for auth, sessions, webhooks, and billing entitlements
- Preact + Vite frontend for fast UI iteration

## Architecture

Django owns schema and migrations. Supabase provides the Postgres infrastructure and optional PostgREST access for RLS-aware queries. Clerk handles auth and billing features, and Django verifies Clerk JWTs through JWKS.

## Repository Layout

```text
backend/
  manage.py
  requirements.txt
  .env.example
  project_settings/
  api/
frontend/
  package.json
  .env.example
  vite.config.js
  src/
```

## Quick Start

### 1) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 manage.py migrate
python3 manage.py runserver
```

Backend runs on `http://127.0.0.1:8000`.

### 2) Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend runs on `http://127.0.0.1:5173`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `DJANGO_DEBUG` | No | `True` for local development |
| `DJANGO_ALLOWED_HOSTS` | No | Comma-separated hosts |
| `DATABASE_URL` | No | Optional DB URL (`postgresql://...` or `sqlite:///...`) |
| `DB_NAME` | No | Used when `DATABASE_URL` is not set |
| `DB_USER` | No | Used when `DATABASE_URL` is not set |
| `DB_PASSWORD` | No | Used when `DATABASE_URL` is not set |
| `DB_HOST` | No | Supabase pooler host |
| `DB_PORT` | No | Default `5432` |
| `CORS_ALLOWED_ORIGINS` | No | Include frontend origin (`http://localhost:5173`) |
| `CSRF_TRUSTED_ORIGINS` | No | Include frontend origin (`http://localhost:5173`) |
| `CLERK_SECRET_KEY` | Yes | Clerk backend secret key |
| `CLERK_DOMAIN` | Yes | Clerk instance domain |
| `CLERK_JWKS_URL` | No | Defaults from `CLERK_DOMAIN` |
| `CLERK_JWT_ISSUER` | No | Defaults from `CLERK_DOMAIN` |
| `CLERK_JWT_AUDIENCE` | No | Optional JWT audience |
| `CLERK_AUTHORIZED_PARTIES` | No | Optional allowed `azp` values |
| `CLERK_BILLING_CLAIM` | No | Entitlements claim key (default: `entitlements`) |
| `CLERK_WEBHOOK_SIGNING_SECRET` | Yes | Svix signing secret |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Server-only key, bypasses RLS |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key |
| `VITE_API_BASE_URL` | Yes | Django API base URL, default `http://127.0.0.1:8000/api` |
| `VITE_CLERK_BILLING_PORTAL_URL` | No | Optional billing portal or pricing URL |

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health/` | Public | Health check |
| `GET` | `/api/me/` | Required | JWT claims and synced profile |
| `GET` | `/api/profile/` | Required | Current user profile model |
| `GET` | `/api/me/clerk/` | Required | Full Clerk user from backend SDK |
| `GET` | `/api/billing/features/` | Required | Enabled features list |
| `GET` | `/api/billing/features/?feature=pro` | Required | Single feature check |
| `GET` | `/api/projects/` | Required | List current user projects |
| `POST` | `/api/projects/` | Required | Create project |
| `GET` | `/api/projects/<id>/` | Required | Get project |
| `PATCH` | `/api/projects/<id>/` | Required | Update project |
| `DELETE` | `/api/projects/<id>/` | Required | Delete project |
| `GET` | `/api/supabase/profile/` | Required | Read `profiles` table via Supabase client |
| `POST` | `/api/webhooks/clerk/` | Svix | Clerk webhook receiver |

## Authentication Flow

Protected endpoints support:
- `Authorization: Bearer <clerk-jwt>`
- Clerk `__session` cookie

Django verifies tokens against Clerk JWKS with supported asymmetric algorithms.

## Billing and Entitlements

Billing access is inferred from Clerk JWT claims. The backend reads `CLERK_BILLING_CLAIM` (default `entitlements`) and exposes feature checks through `/api/billing/features/`.

## Webhooks

1. Create endpoint in Clerk Dashboard -> Webhooks
2. Set endpoint URL to `https://your-domain.com/api/webhooks/clerk/`
3. Copy signing secret into `CLERK_WEBHOOK_SIGNING_SECRET`

Current handlers sync Clerk user lifecycle into the Django `Profile` model:
- `user.created`
- `user.updated`
- `user.deleted`
- `session.created`

## Supabase Usage

`backend/api/supabase_client.py` supports two modes:
- User-scoped client with forwarded Clerk JWT (`access_token=...`) for RLS
- Service-role client (`use_service_role=True`) for trusted server operations

Example RLS policy:

```sql
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
ON profiles FOR SELECT
USING (clerk_user_id = auth.jwt() ->> 'sub');
```

## Run Tests

From `backend/`:

```bash
python3 manage.py test api -v2
```

If your default DB points at a shared remote Postgres, run tests with local SQLite override:

```bash
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2
```

## Production Checklist

- Set `DJANGO_DEBUG=False`
- Use strong `DJANGO_SECRET_KEY`
- Restrict `DJANGO_ALLOWED_HOSTS`
- Set explicit `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`
- Enforce HTTPS
- Use real Clerk and Supabase credentials
- Configure webhook signing secret
- Add and validate RLS policies for Supabase tables
