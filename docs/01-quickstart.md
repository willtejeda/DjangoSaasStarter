# 01 Quickstart

Goal: run the stack locally and pass preflight validation before writing custom features.

## 1. Install requirements

- Python 3.11+
- Node.js 20+
- npm
- Docker optional

## 2. Backend setup

```bash
cd ./backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 manage.py migrate
python3 manage.py runserver
```

Backend URL: `http://127.0.0.1:8000`

## 3. Frontend setup

```bash
cd ./frontend
cp .env.example .env
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:5173`

## 4. Required env values first

`./frontend/.env`

```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

`./backend/.env`

```bash
DJANGO_SECRET_KEY=replace-this-value
DJANGO_DEBUG=True
CLERK_SECRET_KEY=sk_test_xxx
CLERK_DOMAIN=your-domain.clerk.accounts.dev
CLERK_WEBHOOK_SIGNING_SECRET=whsec_xxx
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=eyXXXX
FRONTEND_APP_URL=http://127.0.0.1:5173
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=Acme <updates@yourdomain.com>
BILLING_SYNC_SOFT_STALE_SECONDS=900
BILLING_SYNC_HARD_TTL_SECONDS=10800
```

## 5. Schema ownership rule

Django is schema source of truth.

Use Django models plus migrations for schema changes.
Do not modify Django-managed tables directly in Supabase dashboard.

## 6. Run preflight checks in UI

1. Sign in at `http://127.0.0.1:5173`
2. Open `/app`
3. Complete the **Before You Start** checklist in order:
   - Clerk auth and account sync
   - Supabase profile probe
   - Resend test email
   - Order placement
   - Webhook payment confirmation
   - Subscription plus usage

Do not start product features until all checks pass.

## 7. Billing sync contract quick check

Use cached status for reads and explicit refresh only when needed:

```bash
curl -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8000/api/account/subscriptions/status/"

curl -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8000/api/account/subscriptions/status/?refresh=1"
```

## 8. Health checks from CLI

```bash
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/products/
```

Expected fresh catalog response is `[]`.

## 9. Start scripts

```bash
cd .
./start.sh
```

Flags:

- `START_SKIP_BACKEND=true`
- `START_SKIP_FRONTEND=true`
- `BACKEND_RUN_MIGRATIONS=false`
- `FRONTEND_TYPECHECK_ON_START=false`

## 10. Quality checks

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ./frontend
npm run build
```
