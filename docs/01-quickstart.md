# 01 Quickstart

Goal: run the app locally, confirm stack health, and establish schema ownership rules.

## 1. Prerequisites

- Python 3.11+
- Node.js 20+
- npm
- Docker (optional)

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

Open a second terminal:

```bash
cd ./frontend
cp .env.example .env
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:5173`

## 4. Minimum env values to set first

`frontend/.env`

```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

`backend/.env`

```bash
DJANGO_SECRET_KEY=replace-this-value
DJANGO_DEBUG=True
CLERK_SECRET_KEY=sk_test_xxx
CLERK_DOMAIN=your-domain.clerk.accounts.dev
CLERK_WEBHOOK_SIGNING_SECRET=whsec_xxx
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=eyXXXX
ASSET_STORAGE_BUCKET=digital-assets
FRONTEND_APP_URL=http://127.0.0.1:5173
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=Acme <updates@yourdomain.com>
```

Optional AI provider placeholders:

```bash
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=
```

You can keep remaining values from `.env.example` while bootstrapping locally.

Resend notes:

- `FRONTEND_APP_URL` is used for deep links in email content.
- `RESEND_REPLY_TO_EMAIL` is optional.
- If `RESEND_API_KEY` or `RESEND_FROM_EMAIL` is missing, email sending is skipped.

## 5. Schema ownership check

Django owns schema. Supabase is the Postgres host and operations surface.

Required behavior:

- Change schema via Django `models.py` and migrations.
- Run `python3 manage.py makemigrations` and `python3 manage.py migrate`.

Avoid editing Django-managed tables directly in Supabase dashboard.

## 6. Health checks

```bash
curl http://127.0.0.1:8000/api/health/
```

Expected keys:

```json
{"status":"ok","timestamp":"<iso8601>"}
```

```bash
curl http://127.0.0.1:8000/api/products/
```

Expected on a fresh DB:

```json
[]
```

Open `http://127.0.0.1:5173` and verify homepage renders.

## 7. Start script options

From repo root:

```bash
./start.sh
```

Backend only:

```bash
./backend/start.sh
```

Frontend only:

```bash
./frontend/start.sh
```

Useful flags:

- `START_SKIP_BACKEND=true` to skip backend in root starter
- `START_SKIP_FRONTEND=true` to skip frontend in root starter
- `BACKEND_RUN_MIGRATIONS=false` to skip migrations on backend script start
- `FRONTEND_TYPECHECK_ON_START=false` to skip typecheck on frontend script start

## 8. Self-hosted direction

Recommended default production model:

- Run Django and frontend in Coolify
- Run Supabase with your preferred self-host strategy
- Keep external runtime dependencies limited to Clerk and Resend

## 9. Optional Docker quick run

Build and run backend image:

```bash
docker build -t djangostarter-backend ./backend
docker run --rm -p 8000:8000 --env-file ./backend/.env djangostarter-backend
```

Build and run frontend image:

```bash
docker build -t djangostarter-frontend ./frontend
docker run --rm -p 5173:80 djangostarter-frontend
```

## 10. Quality checks before commit

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ./frontend
npm run build
```
