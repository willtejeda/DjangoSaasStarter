# DjangoStarter

Revenue-first Django starter for creators and small teams that want to ship paid products quickly.

## Mission

Creators do not need more boilerplate.
Creators need cash flow.

This stack helps you launch one reliable paid loop, verify it end to end, then scale.

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

1. `/Users/will/Code/CodexProjects/DjangoStarter/docs/README.md`
2. `/Users/will/Code/CodexProjects/DjangoStarter/docs/01-quickstart.md`
3. `/Users/will/Code/CodexProjects/DjangoStarter/docs/02-first-revenue-loop.md`
4. `/Users/will/Code/CodexProjects/DjangoStarter/docs/03-api-cheatsheet.md`
5. `/Users/will/Code/CodexProjects/DjangoStarter/docs/04-troubleshooting.md`
6. `/Users/will/Code/CodexProjects/DjangoStarter/docs/05-customize-template.md`
7. `/Users/will/Code/CodexProjects/DjangoStarter/docs/06-resend-transactional-email.md`
8. `/Users/will/Code/CodexProjects/DjangoStarter/docs/07-agent-skills-playbook.md`
9. `/Users/will/Code/CodexProjects/DjangoStarter/docs/08-security-pass-phase-1.md`
10. `/Users/will/Code/CodexProjects/DjangoStarter/docs/09-agent-frameworks-2026.md`
11. `/Users/will/Code/CodexProjects/DjangoStarter/docs/StackAnalysis.md`

## Quick start

### Backend

```bash
cd /Users/will/Code/CodexProjects/DjangoStarter/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 manage.py migrate
python3 manage.py runserver
```

### Frontend

```bash
cd /Users/will/Code/CodexProjects/DjangoStarter/frontend
cp .env.example .env
npm install
npm run dev
```

## Quality gates

```bash
cd /Users/will/Code/CodexProjects/DjangoStarter/backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd /Users/will/Code/CodexProjects/DjangoStarter/frontend
npm run build
```

## Frontend map

- Main app shell: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/app.tsx`
- API client: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/lib/api.ts`
- Shared UI helpers: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/app-shell/ui-utils.ts`
- Examples route modules: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/examples/`

## Backend map

- Domain models: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/models/`
- API views: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/views_modules/`
- Integrations and tools: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/tools/`
- Webhooks: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/webhooks/`
- Tests: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/tests/`

## Agent docs

- Agent contract: `/Users/will/Code/CodexProjects/DjangoStarter/AGENTS.md`
- Agent skill templates: `/Users/will/Code/CodexProjects/DjangoStarter/agent-skills/README.md`
