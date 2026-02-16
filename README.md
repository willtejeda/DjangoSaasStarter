# Django + Supabase + Clerk + Preact Commerce Starter

Production-minded starter for selling digital products and services.

## Why This Stack

This stack is opinionated on purpose.

- `Django` is the brain.
Django owns schema, migrations, data integrity, fulfillment workflows, and API contracts.
- `Supabase` is your managed Postgres control plane.
You get hosted Postgres, backups, SQL tools, and a cleaner data ops surface than relying only on Django admin.
- `Clerk` handles authentication and billing.
You offload auth/session complexity and use Clerk Billing for subscriptions and checkout.
- `Preact` keeps frontend payloads small.
You ship faster pages with less JS overhead while keeping React-compatible patterns.

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

### 3) Start Scripts

```bash
# from repository root
./start.sh

# or run each app separately
cd backend && ./start.sh
cd frontend && ./start.sh
```

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
| `CLERK_BILLING_CLAIM` | No | Entitlements claim key (`entitlements` default) |
| `CLERK_WEBHOOK_SIGNING_SECRET` | Yes | Svix signing secret |
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

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key |
| `VITE_API_BASE_URL` | Yes | Django API base URL (`http://127.0.0.1:8000/api`) |
| `VITE_CLERK_BILLING_PORTAL_URL` | No | Optional direct billing portal link |

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

These keys should map to your product entitlements and paywall checks in Django/Preact.

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
- `billing.subscription.created`, `billing.subscription.updated`, `billing.subscription.active`, `billing.subscription.paused`, `billing.subscription.canceled`

Webhook events are also saved to local `WebhookEvent` for idempotency and audit history.

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

### Buyer account

- `GET/PATCH /api/account/customer/`
- `GET /api/account/orders/`
- `POST /api/account/orders/create/`
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
    "clerk_price_id": "price_xxx"
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

## Test Commands

From `backend/`:

```bash
python3 manage.py test api -v2
```

If your default DB points at remote Postgres, run tests with local SQLite:

```bash
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2
```
