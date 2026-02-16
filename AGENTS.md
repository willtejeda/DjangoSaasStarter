# DjangoStarter Agent Contract

This repository is optimized for autonomous coding agents (Codex, Claude Code, OpenCode).

## Mission

Ship deployable, monetized MVPs fast with safe defaults.

## Stack

- Backend: Django + DRF (`backend/`)
- Frontend: React 19 + Vite (`frontend/`)
- Auth and Billing: Clerk
- Database: Supabase Postgres (or local SQLite for tests)

## Critical Rules

1. Never bypass payment verification in production.
2. Rely on verified Clerk webhooks for payment fulfillment.
3. Keep `DJANGO_DEBUG=False` in production.
4. Do not store secrets in git.
5. Run tests and build before proposing changes.

## Agent Objective

Convert this template into a custom SaaS product with a revenue-first workflow, while preserving payment and security contracts.

## SaaS Conversion Playbook

Follow this order. Do not skip steps.

### Step 1: Define the business target

Gather or infer:

- Ideal customer profile
- Core pain solved
- Primary paid offer
- Entry price and upsell path
- 30 day success metric

Output required:

- One sentence positioning statement
- One clear offer promise

### Step 2: Adapt marketing surfaces first

Edit frontend messaging in `frontend/src/app.tsx` before deep backend changes.

Minimum updates:

- Hero headline and subheadline
- Offer cards and benefit bullets
- CTA labels and destination paths
- Pricing page support copy

Goal: a new visitor should understand who the product is for, what it does, and why to buy.

### Step 3: Model catalog and pricing

Use seller endpoints to configure product catalog:

1. Create products (`digital` or `service`)
2. Create prices with correct billing period
3. Mark one default active price
4. Attach feature keys for entitlement gating

Do not hardcode pricing in frontend.

### Step 4: Wire fulfillment correctly

For digital offers:

- Attach digital assets
- Verify download grant creation after order fulfillment

For service offers:

- Configure service offer fields
- Verify booking creation after fulfillment

### Step 5: Keep payment truth server-side

Non negotiable production behavior:

- `POST /api/account/orders/create/` creates pending orders
- Clerk payment events confirm payment via `/api/webhooks/clerk/`
- Fulfillment occurs only after verified webhook or approved local-only manual flow

Local-only fallback controls:

- `ORDER_CONFIRM_ALLOW_MANUAL`
- `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM`
- `VITE_ENABLE_DEV_MANUAL_CHECKOUT`

Set these to safe defaults in production.

### Step 6: Validate account UX

Check signed-in paths:

- `/app`
- `/account/purchases`
- `/account/subscriptions`
- `/account/downloads`
- `/account/bookings`

Each page should load without console errors and show correct empty or populated states.

### Step 7: Ship only after quality gates

Run all required checks:

```bash
cd backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ../frontend
npm run build
```

Document in PR:

1. What changed.
2. Why it changed.
3. Test and build results.
4. Migration, env, and deploy impacts.

## Key Commands

### Backend

```bash
cd backend
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

```bash
cd backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
```

```bash
cd backend
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run build
```

## Payment Flow Contract

1. `POST /api/account/orders/create/` creates pending order.
2. Checkout happens in Clerk.
3. Clerk webhook events (`paymentAttempt.*`, `checkout.*`) mark order paid.
4. Fulfillment runs server-side only after verified webhook.

Direct client-side order confirmation is disabled by default and must not be enabled in production.

## Environment Flags Worth Knowing

- `ORDER_CONFIRM_ALLOW_MANUAL`
- `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM`
- `ORDER_CONFIRM_SHARED_SECRET`
- `VITE_ENABLE_DEV_MANUAL_CHECKOUT` (development only)

## Deploy Notes

- Frontend SPA rewrites are provided for Vercel and Netlify.
- CI runs backend deploy checks, backend tests, and frontend build.

## Docs For Humans and Agents

Start here:

- `docs/README.md`
- `docs/01-quickstart.md`
- `docs/02-first-revenue-loop.md`
- `docs/03-api-cheatsheet.md`
- `docs/04-troubleshooting.md`
- `docs/05-customize-template.md`
