# Django + Supabase + Clerk Starter

Django REST API template with Clerk auth/billing and Supabase Postgres.

## Quick Start

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ← edit with your credentials
python3 manage.py migrate
python3 manage.py runserver
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | Change before production |
| `DJANGO_DEBUG` | — | `True` for dev (default) |
| `DJANGO_ALLOWED_HOSTS` | — | Comma-separated (default: `localhost,127.0.0.1`) |
| `DATABASE_URL` | — | PostgreSQL URL (falls back to SQLite) |
| `CORS_ALLOWED_ORIGINS` | — | Comma-separated frontend origins |
| `CSRF_TRUSTED_ORIGINS` | — | Comma-separated trusted origins |
| `CLERK_SECRET_KEY` | ✅ | [Dashboard → API Keys](https://dashboard.clerk.com) |
| `CLERK_DOMAIN` | ✅ | e.g. `abc-123.clerk.accounts.dev` |
| `CLERK_JWKS_URL` | — | Auto-derived from `CLERK_DOMAIN` |
| `CLERK_JWT_ISSUER` | — | Auto-derived from `CLERK_DOMAIN` |
| `CLERK_JWT_AUDIENCE` | — | Audience claim (leave empty to skip) |
| `CLERK_AUTHORIZED_PARTIES` | — | Comma-separated allowed `azp` values |
| `CLERK_BILLING_CLAIM` | — | JWT claim for billing (default: `entitlements`) |
| `CLERK_WEBHOOK_SIGNING_SECRET` | — | [Dashboard → Webhooks](https://dashboard.clerk.com) |
| `SUPABASE_URL` | ✅ | e.g. `https://xxx.supabase.co` |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | — | Bypasses RLS — server-side only |

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health/` | Public | Health check |
| `GET` | `/api/me/` | 🔒 | User from JWT claims |
| `GET` | `/api/me/clerk/` | 🔒 | Full Clerk profile (server-side) |
| `GET` | `/api/billing/features/` | 🔒 | Enabled billing features |
| `GET` | `/api/billing/features/?feature=pro` | 🔒 | Check one feature |
| `GET` | `/api/supabase/profile/` | 🔒 | Profile from `profiles` table |
| `POST` | `/api/webhooks/clerk/` | Svix | Clerk webhook receiver |

## Authentication

Protected endpoints accept:
- `Authorization: Bearer <clerk-jwt>` header
- Clerk `__session` cookie

JWTs verified against Clerk JWKS using RS256/ES256/EdDSA.

## Webhooks

1. [Clerk Dashboard → Webhooks](https://dashboard.clerk.com) → Create endpoint
2. URL: `https://your-domain.com/api/webhooks/clerk/`
3. Copy Signing Secret → `CLERK_WEBHOOK_SIGNING_SECRET` in `.env`

Add your logic in `api/webhooks.py`:

```python
def handle_user_created(data):
    clerk_user_id = data.get("id")
    # Create Supabase profile, send welcome email, etc.
```

## Clerk Backend SDK

```python
from api.clerk_client import get_clerk_client, get_clerk_user

user = get_clerk_user("user_2abc...")

client = get_clerk_client()
client.users.update_metadata(user_id="user_2abc...", ...)
```

## Supabase

Forwards Clerk JWT to PostgREST for Row Level Security:

```python
from api.supabase_client import get_supabase_client

# User-scoped (respects RLS)
client = get_supabase_client(access_token=request.clerk_token)

# Service-role (bypasses RLS)
client = get_supabase_client(use_service_role=True)
```

Example RLS policy:

```sql
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
ON profiles FOR SELECT
USING (clerk_user_id = auth.jwt() ->> 'sub');
```

## Project Structure

```
app/
├── manage.py
├── requirements.txt
├── .env.example
├── project_settings/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── api/
│   ├── authentication.py     # DRF auth backend (JWT verification)
│   ├── clerk.py              # JWKS token decode
│   ├── clerk_client.py       # Backend SDK client
│   ├── middleware.py          # Optional request enrichment
│   ├── supabase_client.py    # Supabase client + RLS forwarding
│   ├── views.py              # API views
│   ├── webhooks.py           # Webhook receiver
│   ├── urls.py
│   ├── models.py
│   └── tests.py
```

## Tests

```bash
python3 manage.py test api -v2
```

## Production Checklist

- [ ] `DJANGO_DEBUG=False`
- [ ] Strong `DJANGO_SECRET_KEY`
- [ ] Restrict `DJANGO_ALLOWED_HOSTS`
- [ ] Explicit `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`
- [ ] HTTPS only
- [ ] Real `CLERK_SECRET_KEY` and `CLERK_WEBHOOK_SIGNING_SECRET`
- [ ] Configure all `SUPABASE_*` keys
- [ ] RLS policies on all Supabase tables
