# DjangoStarter

Revenue-first Django starter for creators and small teams that want to ship paid products quickly.

## Mission

Creators do not need more boilerplate.
Creators need cash flow.

This stack helps you launch one reliable paid loop, verify it end to end, then scale.

## App Summary

### What it is

DjangoStarter is a revenue-first SaaS starter that combines a Django + DRF backend with a React 19 + Vite frontend. It is built to help teams launch paid digital or service offers quickly while keeping payment verification and fulfillment server-side.

### Who it's for

Primary persona: Python developers, solo founders, and small teams that want a self-hosted-first app foundation with modern auth, billing, and checkout scaffolding already wired.

### What it does

- Supports digital and service product catalogs with server-driven prices and feature keys
- Creates pending orders and tracks transactions for one-time and subscription purchases
- Confirms payment via verified Clerk webhook events before fulfillment runs
- Generates entitlements, download grants, and fulfillment/work orders after successful payment
- Provides signed-in account routes for purchases, subscriptions, downloads, and bookings/work orders
- Includes AI provider and usage summary endpoints scaffolded for token, image, and video limits
- Includes preflight checks for auth sync, Supabase probe, email test, and payment flow readiness

### How it works (repo-evidenced architecture)

Components and services:

- Frontend SPA: `frontend/src/main.tsx`, `frontend/src/app.tsx`, `frontend/src/routes/index.tsx`
- Frontend API wrapper: `frontend/src/lib/api.ts`
- Backend API routes: `backend/project_settings/urls.py`, `backend/api/urls.py`
- Domain models: `backend/api/models/accounts.py`, `backend/api/models/catalog.py`, `backend/api/models/commerce.py`
- Webhook verification and handlers: `backend/api/webhooks/receiver.py`, `backend/api/webhooks/handlers.py`
- Integration adapters: `backend/api/tools/auth`, `backend/api/tools/billing`, `backend/api/tools/database`, `backend/api/tools/email`, `backend/api/tools/storage`

Data flow:

1. User loads the React app and signs in through Clerk.
2. Frontend calls `/api/*` endpoints using `apiRequest` and `authedRequest`.
3. Django view modules read and write product, order, subscription, entitlement, and fulfillment models.
4. Clerk webhook events hit `/api/webhooks/clerk/`, are verified, deduplicated, and dispatched.
5. Successful payment events update order state and trigger server-side fulfillment artifacts.
6. Account routes read purchases, subscriptions, downloads, and work orders from backend APIs.

Background queue or worker architecture: Not found in repo.

### How to run (minimal)

1. Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env && python3 manage.py migrate && python3 manage.py runserver`
2. Frontend: `cd frontend && cp .env.example .env && npm install && npm run dev`
3. Set `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env` before frontend startup

## Who this is for

- Python developers who want modern React UX without rebuilding auth or billing
- Solo founders and creators launching digital products or subscriptions
- AI product builders who need token, image, and video usage scaffolding
- Teams that want self-hosted control with low monthly overhead

## Why DjangoStarter instead of a JS-only starter

- Django ORM and migrations give explicit schema control and predictable refactors
- Python ecosystem fits AI workloads and model integrations naturally
- Clerk handles auth and billing complexity so you do not rebuild identity
- Supabase gives a strong operator surface for Postgres and realtime
- You keep frontend flexibility with React + Tailwind

## Core architecture

- Backend: Django + DRF
- Frontend: React 19 + Vite + Tailwind
- Auth and billing: Clerk
- Database and ops surface: Supabase Postgres
- Transactional email: Resend (with Premailer CSS inlining support)
- Deploy model: self-host app and Supabase (Coolify-friendly), keep only Clerk and Resend external

## Non negotiable contracts

1. Django owns schema and migrations.
2. Clerk webhooks are payment truth in production.
3. Fulfillment happens server-side only after verified payment.
4. No secrets in git.
5. `DJANGO_DEBUG=False` in production.

## Before building features

Run `/app` and complete the **Before You Start** preflight checks:

1. Clerk auth and account sync
2. Supabase profile probe
3. Resend test email
4. Order placement test
5. Webhook payment confirmation test
6. Subscription plus usage test

If these fail, fix integrations before writing product-specific code.

## Docs map (wiki)

Read in this order:

1. `./docs/README.md`
2. `./docs/01-quickstart.md`
3. `./docs/02-first-revenue-loop.md`
4. `./docs/03-api-cheatsheet.md`
5. `./docs/04-troubleshooting.md`
6. `./docs/05-customize-template.md`
7. `./docs/06-resend-transactional-email.md`
8. `./docs/07-agent-skills-playbook.md`
9. `./docs/08-security-pass-phase-1.md`
10. `./docs/09-agent-frameworks-2026.md`
11. `./docs/10-agent-framework-examples.md`
12. `./docs/11-name-ideas.md`
13. `./docs/12-frontend-starter-blueprint.md`
14. `./docs/StackAnalysis.md`

## Doc quick links by task

- First revenue loop: `./docs/02-first-revenue-loop.md`
- API endpoint lookup: `./docs/03-api-cheatsheet.md`
- Customizing routes and modules: `./docs/05-customize-template.md`
- Resend email templates and delivery test: `./docs/06-resend-transactional-email.md`
- Agent workflow and skills: `./docs/07-agent-skills-playbook.md`
- Security pass details: `./docs/08-security-pass-phase-1.md`
- Agent framework comparison: `./docs/09-agent-frameworks-2026.md`
- Agent framework code examples: `./docs/10-agent-framework-examples.md`
- Frontend route and component blueprint: `./docs/12-frontend-starter-blueprint.md`

## Quick start

### Backend

```bash
cd ./backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 manage.py migrate
python3 manage.py runserver
```

### Frontend

```bash
cd ./frontend
cp .env.example .env
npm install
npm run dev
```

## Quality gates

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ./frontend
npm run build
```

## Frontend map

- App bootstrap: `./frontend/src/app.tsx`
- Route composition: `./frontend/src/routes/index.tsx`
- Landing page route: `./frontend/src/routes/landing/page.tsx`
- Pricing route: `./frontend/src/routes/pricing/page.tsx`
- Product routes: `./frontend/src/routes/products/`
- Signed-in dashboard route: `./frontend/src/routes/app/dashboard/page.tsx`
- Signed-in account routes: `./frontend/src/routes/app/account/`
- Examples route: `./frontend/src/routes/examples/page.tsx`
- Layout components: `./frontend/src/components/layout/app-shell.tsx`
- Feedback components: `./frontend/src/components/feedback/toast.tsx`
- API client: `./frontend/src/lib/api.ts`
- Shared helper modules: `./frontend/src/shared/`
- Static assets: `./frontend/public/`

## Frontend UX layout contract

- Desktop (`lg` and up): persistent left sidebar is the navigation surface.
- Mobile and tablet (`< lg`): the same sidebar content opens via a hamburger-triggered drawer.
- Keep navigation in one place (sidebar content), not split between sidebar and top navbar.
- The app shell should use full-width content with a dedicated left rail, not a centered fixed-width canvas.
- Keep route orchestration in `./frontend/src/routes/index.tsx` and shared nav primitives in `./frontend/src/components/layout/app-shell.tsx`.

## Backend map

- Domain models: `./backend/api/models/`
- API views: `./backend/api/views_modules/`
- Integrations and tools: `./backend/api/tools/`
- Webhooks: `./backend/api/webhooks/`
- Tests: `./backend/api/tests/`

## Agent docs

- Agent contract: `./AGENTS.md`
- Agent skill templates: `./agent-skills/README.md`

## TODO (Phase 2)

- Build a production-safe coding agent widget with guarded dev-only access and OpenRouter-compatible providers.
- Track evaluation and framework decision updates in:
  - `./docs/09-agent-frameworks-2026.md`
  - `./docs/10-agent-framework-examples.md`
  - `./docs/07-agent-skills-playbook.md`
