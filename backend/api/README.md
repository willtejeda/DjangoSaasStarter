# Backend API Module Map

## Directory structure

- `./backend/api/models/`
  - `accounts.py`
  - `catalog.py`
  - `commerce.py`
- `./backend/api/serializers/`
  - `common.py`
  - `catalog.py`
  - `commerce.py`
- `./backend/api/views_modules/`
  - `common.py`
  - `account.py`
  - `seller.py`
  - `helpers.py`
- `./backend/api/webhooks/`
  - `verification.py`
  - `helpers.py`
  - `handlers.py`
  - `receiver.py`
- `./backend/api/tools/`
  - `auth/`
  - `billing/`
  - `database/`
  - `email/`
  - `storage/`
- `./backend/api/tests/`

## Contracts

1. Django owns schema and migrations.
2. Clerk webhooks confirm payments in production.
3. Fulfillment runs server-side only.
4. Tools are integration adapters and should stay swappable.

## Logging and safety

- API logs are enabled through `API_LOG_LEVEL`.
- Error internals are only exposed in responses when `DJANGO_DEBUG=True`.

## Key commands

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy
```
