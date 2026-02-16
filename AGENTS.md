# DjangoStarter Agent Contract

This repository is optimized for autonomous coding agents (Codex, Claude Code, OpenCode).

## Mission

Ship deployable, monetized MVPs fast with safe defaults.

## Positioning

Creators do not need more boilerplate. They need cash flow.

DjangoStarter is a self-hosted-first SaaS starter for Python builders who want:

- Fast product shipping
- Strict payment and fulfillment integrity
- Modular scaffolding they can keep or delete
- AI-first subscription and usage support

## Stack

- Backend: Django + DRF (`backend/`)
- Frontend: React 19 + Vite + Tailwind (`frontend/`)
- Auth and Billing: Clerk
- Database: Supabase Postgres (or local SQLite for tests)
- Email: Resend
- Deployment baseline: Coolify + self-hosted app and Supabase

## Non Negotiables

1. Never bypass payment verification in production.
2. Rely on verified Clerk webhooks for payment fulfillment.
3. Keep `DJANGO_DEBUG=False` in production.
4. Do not store secrets in git.
5. Run tests and build before proposing changes.
6. Django owns schema and migrations.

## Schema Ownership Contract

Django is the only source of truth for schema.

Required:

- Create and modify tables via Django models and migrations.
- Run `makemigrations` and `migrate` from Django.

Allowed in Supabase dashboard:

- Querying data
- Operational maintenance
- Auth/RLS and platform settings
- Observability and realtime operations

Not allowed:

- Creating or mutating Django-managed tables directly in Supabase dashboard

## UX and Offer First Workflow

Before implementing major features, define these from the user point of view:

1. Who pays and why now?
2. What exact outcome is promised in 7 days?
3. What does the first checkout unlock immediately?

Then execute in this order:

1. Update messaging surfaces in `frontend/src/app.tsx`
2. Validate one paid loop end to end
3. Expand feature depth only after paid loop integrity is proven

## SaaS Conversion Playbook

Follow this order. Do not skip steps.

### Step 1: Define business target

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

Edit `frontend/src/app.tsx` before deep backend changes.

Minimum updates:

- Hero headline and subheadline
- Offer cards and benefits
- CTA labels and destination paths
- Pricing support copy

Goal: first-time visitors should understand who this is for, what it does, and why they should buy now.

### Step 3: Model catalog and pricing

Use seller endpoints to configure catalog:

1. Create products (`digital` or `service`)
2. Create prices with correct billing period
3. Mark one default active price
4. Attach feature keys for entitlement gating

Do not hardcode pricing in frontend.

### Step 4: Validate digital commerce tutorial

For digital offers:

- Attach digital assets
- Confirm purchase creates fulfillment and download grants
- Confirm account downloads route works

### Step 5: Validate subscription plus usage tutorial

For recurring offers:

- Create monthly or yearly plan
- Verify webhook-driven subscription state
- Configure usage expectations for AI features (tokens, images, videos)
- Confirm account subscriptions view and AI usage summary view

### Step 6: Configure AI provider scaffolding

Use environment-driven placeholders for:

- `OPENROUTER_*`
- `OLLAMA_*`

Keep integration modular so users can delete or replace provider adapters.

### Step 7: Keep payment truth server-side

Production behavior:

- `POST /api/account/orders/create/` creates pending orders
- Clerk payment events confirm payment via `/api/webhooks/clerk/`
- Fulfillment runs only after verified webhook or approved local-only manual flow

Local-only fallback controls:

- `ORDER_CONFIRM_ALLOW_MANUAL`
- `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM`
- `VITE_ENABLE_DEV_MANUAL_CHECKOUT`

Set these to safe defaults in production.

### Step 8: Validate account UX

Check signed-in paths:

- `/app`
- `/account/purchases`
- `/account/subscriptions`
- `/account/downloads`
- `/account/bookings`

Each page should load without console errors and show correct empty or populated states.

### Step 9: Ship only after quality gates

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

## Tailwind and UI Rule

UI should be utility-first Tailwind in component code.

- Prefer Tailwind classes in JSX/TSX.
- Avoid adding custom stylesheet systems that require end users to hand-write CSS.
- Keep layouts mobile-friendly and conversion-focused.

## Optional Django Extensions (Recommended)

These are optional hardening upgrades and should be introduced deliberately:

- `django-csp`: strong Content Security Policy for Django 4/5 projects
- `drf-spectacular`: OpenAPI schema generation for API-first teams
- `django-axes`: login abuse protection if you add Django credential auth
- `sentry-sdk`: production error monitoring and performance traces

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
- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_DEFAULT_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

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
