# 01 Quickstart

Goal: run the app locally and confirm the stack is healthy.

## 1. Prerequisites

- Python 3.11+
- Node.js 20+
- npm

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

Backend will run on `http://127.0.0.1:8000`.

## 3. Frontend setup

Open a second terminal:

```bash
cd ./frontend
cp .env.example .env
npm install
npm run dev
```

Frontend will run on `http://127.0.0.1:5173`.

## 4. Required env values to verify first

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
```

You can leave many other vars at defaults for local development.

## 5. Health checks

```bash
curl http://127.0.0.1:8000/api/health/
```

Expected shape:

```json
{"status":"ok","timestamp":"2026-02-16T00:00:00+00:00"}
```

```bash
curl http://127.0.0.1:8000/api/products/
```

Expected on a fresh DB:

```json
[]
```

Open `http://127.0.0.1:5173` and verify the marketing homepage loads.

## 6. One-command local start (optional)

From repo root:

```bash
cd .
./start.sh
```

This starts backend and frontend together.

## 7. Quality checks before commit

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ./frontend
npm run build
```
