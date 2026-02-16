# DjangoStarter: Cashflow First SaaS Starter (Django + Supabase + Clerk + Resend + React)

Production-minded starter for creators who want to ship paid products fast without breaking payment or fulfillment trust.

## Documentation Map

Read these docs in order:

1. `docs/01-quickstart.md`
2. `docs/02-first-revenue-loop.md`
3. `docs/03-api-cheatsheet.md`
4. `docs/04-troubleshooting.md`
5. `docs/05-customize-template.md`
6. `docs/06-resend-transactional-email.md`
7. `docs/StackAnalysis.md`

## Why This Stack

This stack is opinionated on purpose.

- `Django` is the brain.
Django owns schema, migrations, data integrity, fulfillment workflows, and API contracts.
- `Supabase` is your managed Postgres control plane.
You get hosted Postgres, backups, SQL tools, and a cleaner data ops surface than relying only on Django admin.
- `Clerk` handles authentication and billing.
You offload auth/session complexity and use Clerk Billing for subscriptions and checkout.
- `Resend` handles lifecycle communication.
You can send offer updates, fulfillment notices, and transactional support messages.
- `React 19` keeps the frontend modern and ecosystem-compatible.
You can pair native React with signal-based state patterns for low-friction reactivity and Tailwind-first UI customization.

## Self Hosted by Default

The default operating model is:

- Deploy Django app with Coolify
- Deploy Supabase with your own infra strategy
- Keep only two external runtime dependencies:
  - Clerk for auth and billing
  - Resend for outbound email

This keeps ongoing costs lower while preserving strong product control.

## Questions New Users Ask

### Why do I need this starter?

Because shipping an MVP is not the hard part. Shipping stable payments, fulfillment, and account lifecycle flows is.
This starter removes that risk layer so you can focus on offer quality and distribution.

### What problem does this solve?

Most early SaaS builds lose weeks rebuilding the same platform plumbing:

- Authentication and billing wiring
- Checkout to paid order state transitions
- Fulfillment and entitlement delivery after payment
- Customer account views for purchases, downloads, subscriptions, and bookings
- AI-ready subscription usage surfaces for tokens, images, and video

DjangoStarter gives you those foundations already connected so you can ship a paid product faster with fewer production mistakes.

## Schema Ownership Rules

Django owns schema and migrations. Keep this strict.

- Use Django models plus migrations for schema changes.
- Run `python3 manage.py makemigrations` then `python3 manage.py migrate`.
- Treat Supabase dashboard as an operations surface, not a parallel schema editor.
- If tables are Django-managed, do not create or mutate them directly in Supabase UI.

This contract keeps AI-assisted coding and production data integrity aligned.

## What Ships Now

### Backend domains

- Auth and profile sync from Clerk JWT and webhooks
- Product catalog and pricing models
- Orders, order items, payment transactions
- Subscriptions synced from Clerk Billing lifecycle events
- Entitlements and fulfillment logic
- Digital assets and download grants
- Service offers and booking requests
- Seller management APIs for products, prices, assets, and service offer config

### Frontend pages

- `/` Marketing homepage
- `/pricing` Clerk PricingTable billing page
- `/products` Public catalog
- `/products/:slug` Product detail and purchase flow
- `/app` Signed-in customer account dashboard
- `/account/purchases`
- `/account/subscriptions`
- `/account/downloads`
- `/account/bookings`
- `/checkout/success`
- `/checkout/cancel`

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
  vite.config.ts
  src/
```

Code organization references:

- Backend API module map: `backend/api/README.md`
- Backend tools map: `backend/api/tools/README.md`
- Frontend module map: `frontend/src/README.md`

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

### 3) Start Scripts

```bash
# from repository root
./start.sh

# or run each app separately
cd backend && ./start.sh
cd frontend && ./start.sh
```

Useful flags:

- `START_SKIP_BACKEND=true`
- `START_SKIP_FRONTEND=true`
- `BACKEND_RUN_MIGRATIONS=false`
- `FRONTEND_TYPECHECK_ON_START=false`

### 4) Docker Images (Backend and Frontend)

Build backend image:

```bash
docker build -t djangostarter-backend ./backend
```

Run backend image:

```bash
docker run --rm -p 8000:8000 --env-file ./backend/.env djangostarter-backend
```

Build frontend image:

```bash
docker build -t djangostarter-frontend ./frontend
```

Run frontend image:

```bash
docker run --rm -p 5173:80 djangostarter-frontend
```

## Before You Start Building Features

Use the signed-in dashboard (`/app`) preflight validator to confirm integrations first:

1. Clerk auth and profile sync
2. Supabase bridge probe
3. Resend delivery test email
4. Order placement test
5. Webhook payment confirmation test
6. Subscription plus usage test

This catches infrastructure misconfiguration before product feature work begins.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `DJANGO_DEBUG` | No | `True` for local development |
| `DJANGO_ALLOWED_HOSTS` | No | Comma-separated hosts |
| `DJANGO_SECURE_SSL_REDIRECT` | No | Force HTTPS redirects (`True` recommended in production) |
| `DJANGO_SECURE_HSTS_SECONDS` | No | HSTS max age in seconds (`31536000` in production) |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | No | Include subdomains for HSTS in production |
| `DJANGO_SECURE_HSTS_PRELOAD` | No | Enable HSTS preload flag in production |
| `DJANGO_SESSION_COOKIE_SECURE` | No | Secure-only session cookies in production |
| `DJANGO_CSRF_COOKIE_SECURE` | No | Secure-only CSRF cookies in production |
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
| `CLERK_BILLING_CLAIM` | No | Entitlements claim key (`entitlements` default) |
| `CLERK_WEBHOOK_SIGNING_SECRET` | Yes | Svix signing secret |
| `ORDER_CONFIRM_ALLOW_MANUAL` | No | Allow manual payment confirmation endpoint (development only) |
| `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM` | No | Allow direct client-side Clerk confirmation endpoint (development only) |
| `ORDER_CONFIRM_SHARED_SECRET` | No | Optional `X-Order-Confirm-Secret` value for any direct confirmation call |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Server-only Supabase key |
| `ASSET_STORAGE_BACKEND` | No | `supabase` (default) or `s3` |
| `ASSET_STORAGE_BUCKET` | Yes | Bucket/container used for digital asset objects |
| `ASSET_STORAGE_SIGNED_URL_TTL_SECONDS` | No | Signed download URL lifetime in seconds (default `600`) |
| `ASSET_STORAGE_S3_ENDPOINT_URL` | No | S3 compatible endpoint URL (required for most non-AWS providers) |
| `ASSET_STORAGE_S3_REGION` | No | Region for S3 signing (default `us-east-1`) |
| `ASSET_STORAGE_S3_ACCESS_KEY_ID` | No | S3 access key (required when backend is `s3`) |
| `ASSET_STORAGE_S3_SECRET_ACCESS_KEY` | No | S3 secret key (required when backend is `s3`) |
| `FRONTEND_APP_URL` | No | Frontend origin used for deep-links in transactional emails |
| `RESEND_API_KEY` | No | Resend API key for transactional email delivery |
| `RESEND_FROM_EMAIL` | No | Verified sender identity for outbound emails (`Name <email@domain>`) |
| `RESEND_REPLY_TO_EMAIL` | No | Optional reply-to email address |
| `RESEND_TIMEOUT_SECONDS` | No | Outbound request timeout for Resend API calls (default `10`) |
| `OPENROUTER_API_KEY` | No | Optional key to enable OpenRouter provider placeholder |
| `OPENROUTER_BASE_URL` | No | OpenRouter base URL (`https://openrouter.ai/api/v1` default) |
| `OPENROUTER_DEFAULT_MODEL` | No | Default model hint shown in AI provider surfaces |
| `OLLAMA_BASE_URL` | No | Ollama server URL (`http://127.0.0.1:11434` default) |
| `OLLAMA_MODEL` | No | Ollama model slug to mark local provider as configured |
| `DRF_THROTTLE_ANON` | No | Default anonymous API throttle rate |
| `DRF_THROTTLE_USER` | No | Default authenticated API throttle rate |
| `DRF_THROTTLE_CHECKOUT_CREATE` | No | Throttle for `POST /api/account/orders/create/` |
| `DRF_THROTTLE_ORDER_CONFIRM` | No | Throttle for `POST /api/account/orders/<public_id>/confirm/` |
| `DRF_THROTTLE_DOWNLOAD_ACCESS` | No | Throttle for `POST /api/account/downloads/<token>/access/` |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key |
| `VITE_API_BASE_URL` | Yes | Django API base URL (`http://127.0.0.1:8000/api`) |
| `VITE_CLERK_BILLING_PORTAL_URL` | No | Optional direct billing portal link |
| `VITE_ENABLE_DEV_MANUAL_CHECKOUT` | No | Development-only manual fallback when no checkout URL is configured |

## Resend Transactional Email Setup

The starter now supports Resend for transactional buyer communication.

Implemented events:

- Order fulfillment confirmation
- Booking request confirmation

Setup:

1. Create a domain and sender in Resend.
2. Create an API key in Resend dashboard.
3. Set `RESEND_API_KEY` and `RESEND_FROM_EMAIL` in `backend/.env`.
4. Set `FRONTEND_APP_URL` so email links route buyers to the correct app.

Notes:

- Email delivery is best-effort and does not block checkout or booking creation.
- Requests use idempotency keys per event to reduce duplicate sends.

See `docs/06-resend-transactional-email.md` for the full operator guide and troubleshooting flow.

## AI First Subscription Scaffolding

The starter includes modular placeholders for usage-aware AI subscriptions.

Current built-in endpoints:

- `GET /api/ai/providers/`
- `GET /api/ai/usage/summary/`

Use these to bootstrap:

- OpenRouter-backed remote model products
- Ollama-backed local model products
- Token, image, and video usage displays in account UX

These usage values are starter placeholders. Replace with your own provider telemetry pipeline when you wire production generation workloads.

## Clerk Billing Setup (Products, Plans, Subscriptions)

Use Clerk Billing as the checkout and subscription system, and keep Django as local source of truth for fulfillment and analytics.

### Step 1: Enable Billing and connect your payment processor

In Clerk Dashboard:

1. Open your application.
2. Open `Billing`.
3. Complete setup and connect Stripe.

Reference:
- [Billing overview](https://clerk.com/docs/guides/billing/overview)
- [Set up Billing in dashboard](https://clerk.com/docs/guides/billing/dashboard)

### Step 2: Create plans and features in Clerk

Define plans around outcomes and entitlement keys.

Suggested pattern:

- `free`: onboarding, community access
- `plus`: reminders, reports
- `pro`: ai_coach, priority_support

These keys should map to your product entitlements and paywall checks in Django/React.

Reference:
- [B2C billing guide](https://clerk.com/docs/guides/billing/b2c-guide)

### Step 3: Use Clerk PricingTable in the app

Pricing page is already wired using Clerk React `PricingTable` component.

Reference:
- [Control components guide](https://clerk.com/docs/guides/development/components/control/clerk-components)

### Step 4: Pin Clerk SDK while Billing APIs are evolving

Billing controls like `SubscriptionDetailsButton` are still under the Clerk experimental surface.
This starter pins `@clerk/clerk-react` in `frontend/package.json` to reduce break risk.

### Step 5: Map Clerk plan IDs to local prices

For each local `Price`, set:

- `clerk_plan_id`
- `clerk_price_id` (optional but recommended)

You can set these via seller APIs. This keeps local order/subscription records aligned with Clerk payloads.

### Step 6: Configure webhooks

Create Clerk webhook endpoint:

- URL: `https://<your-domain>/api/webhooks/clerk/`
- Secret: set `CLERK_WEBHOOK_SIGNING_SECRET`

This starter handles:

- `user.created`, `user.updated`, `user.deleted`
- `subscription.created`, `subscription.updated`, `subscription.active`, `subscription.pastDue`, `subscription.canceled`
- `paymentAttempt.created`, `paymentAttempt.updated`
- `checkout.created`, `checkout.updated`

Legacy compatibility aliases are also supported for `billing.subscription.*` and `billing.checkout.*` payload names.

Webhook events are also saved to local `WebhookEvent` for idempotency and audit history.

### Step 7: Link Clerk payment events to local orders

To let webhooks confirm one-time purchases automatically, include local order metadata in your Clerk checkout/payment flow:

- `order_public_id` = local Django `Order.public_id`

Webhook handlers try multiple fields, but `order_public_id` is the most reliable mapping key.

## Checkout and Fulfillment Security

- Production default is webhook-first payment confirmation.
- Direct client-side order confirmation is disabled by default.
- Manual confirmation is disabled by default.
- If you must enable direct confirmation for development, gate it with `ORDER_CONFIRM_SHARED_SECRET` and never expose that secret in frontend code.
- In production keep `ORDER_CONFIRM_ALLOW_MANUAL=False`.
- In production keep `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=False`.

## Commerce Model Map

Implemented models in `backend/api/models.py`:

- `Profile`
- `CustomerAccount`
- `Product`
- `Price`
- `Order`
- `OrderItem`
- `Subscription`
- `PaymentTransaction`
- `WebhookEvent`
- `Entitlement`
- `DigitalAsset`
- `DownloadGrant`
- `ServiceOffer`
- `Booking`
- plus existing `Project` planning model

## API Endpoints

### Public

- `GET /api/health/`
- `GET /api/products/`
- `GET /api/products/<slug>/`

### Auth and profile

- `GET /api/me/`
- `GET /api/profile/`
- `GET /api/me/clerk/`
- `GET /api/billing/features/`
- `GET /api/billing/features/?feature=pro`

### AI scaffolding

- `GET /api/ai/providers/`
- `GET /api/ai/usage/summary/`

### Buyer account

- `GET/PATCH /api/account/customer/`
- `GET /api/account/orders/`
- `POST /api/account/orders/create/`
- `POST /api/account/preflight/email-test/`
- `POST /api/account/orders/<public_id>/confirm/`
- `GET /api/account/subscriptions/`
- `GET /api/account/entitlements/`
- `GET /api/account/downloads/`
- `POST /api/account/downloads/<token>/access/`
- `GET/POST /api/account/bookings/`

### Seller management

- `GET/POST /api/seller/products/`
- `GET/PATCH/DELETE /api/seller/products/<id>/`
- `GET/POST /api/seller/products/<product_id>/prices/`
- `GET/PATCH/DELETE /api/seller/prices/<id>/`
- `GET/POST /api/seller/products/<product_id>/assets/`
- `GET/PATCH/DELETE /api/seller/assets/<id>/`
- `GET/PUT/PATCH /api/seller/products/<product_id>/service-offer/`

### Other integrations

- `GET /api/projects/`
- `POST /api/projects/`
- `GET/PATCH/DELETE /api/projects/<id>/`
- `GET /api/supabase/profile/`
- `POST /api/webhooks/clerk/`

## Example Seller Flow

### Create product

```bash
curl -X POST http://127.0.0.1:8000/api/seller/products/ \
  -H "Authorization: Bearer <clerk-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Creator Bundle",
    "slug": "creator-bundle",
    "product_type": "digital",
    "visibility": "published",
    "feature_keys": ["templates_pack", "priority_support"]
  }'
```

### Add price

```bash
curl -X POST http://127.0.0.1:8000/api/seller/products/<product_id>/prices/ \
  -H "Authorization: Bearer <clerk-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monthly",
    "amount_cents": 2900,
    "currency": "USD",
    "billing_period": "monthly",
    "is_default": true,
    "clerk_plan_id": "plan_xxx",
    "clerk_price_id": "price_xxx",
    "metadata": {
      "checkout_url": "https://checkout.clerk.com/..."
    }
  }'
```

### Add digital asset

```bash
curl -X POST http://127.0.0.1:8000/api/seller/products/<product_id>/assets/ \
  -H "Authorization: Bearer <clerk-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bundle ZIP",
    "file_path": "files/creator-bundle-v1.zip",
    "is_active": true
  }'
```

## Authentication Flow

Protected endpoints support:

- `Authorization: Bearer <clerk-jwt>`
- Clerk `__session` cookie

Django verifies tokens against Clerk JWKS and enforces CSRF checks for cookie-authenticated unsafe methods.

## Optional Django Hardening Extensions

If you want stronger production posture, these are common next adds:

- `django-csp` for explicit Content Security Policy headers on Django 4/5
- `drf-spectacular` for OpenAPI schema generation and client SDK workflows
- `django-axes` for anti-bruteforce login controls when adding Django credential auth
- `sentry-sdk` for production error and performance monitoring

Keep these optional so the starter remains lightweight and modular.

## Test Commands

From `backend/`:

```bash
python3 manage.py test api -v2 --noinput
```

If your default DB points at remote Postgres, run tests with local SQLite:

```bash
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
```

Deploy checks from `backend/`:

```bash
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy
```

Frontend production build from `frontend/`:

```bash
npm run build
```

## Deployment Notes

- Frontend SPA rewrites:
  - Vercel config at `frontend/vercel.json`
  - Netlify config at `frontend/netlify.toml`
- CI workflow at `.github/workflows/ci.yml` runs:
  - Django deploy checks
  - Django API tests
  - Frontend production build
