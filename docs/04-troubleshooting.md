# 04 Troubleshooting

## Preflight step fails in `/app`

Use this order:

1. Check backend logs
2. Check browser network tab
3. Re-run failing step from the preflight card
4. Confirm env vars match `.env.example`

## Supabase probe fails

Symptoms:

- `/api/supabase/profile/` returns `ok: false`

Checks:

1. `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
2. `profiles` table exists
3. RLS policy permits expected access pattern
4. Clerk token forwarding is valid

## Resend email test fails

Symptoms:

- Preflight email step returns error

Checks:

1. `RESEND_API_KEY` and `RESEND_FROM_EMAIL` set in backend env
2. Sender domain is verified in Resend
3. Customer account has a valid billing or profile email
4. Network can reach `https://api.resend.com`

## Order does not become paid

Symptoms:

- Order remains `pending_payment`

Checks:

1. Clerk webhook endpoint configured: `/api/webhooks/clerk/`
2. `CLERK_WEBHOOK_SIGNING_SECRET` is correct
3. Webhook events are delivered without signature errors
4. Matching metadata lets backend map checkout to order

## Download link generation fails

Checks:

1. `ASSET_STORAGE_BACKEND` and related storage env vars are set
2. Asset path exists in storage
3. Bucket or object permissions allow signed URL generation

## Subscription or usage missing

Checks:

1. Recurring price exists and was used in checkout
2. Subscription record exists in `/api/account/subscriptions/`
3. Entitlements are present in `/api/account/entitlements/`
4. `/api/ai/usage/summary/` returns expected buckets

## Frontend shows generic server error

By default production UI hides raw 5xx internals.

If you need raw backend error detail in local debugging:

```bash
# frontend/.env
VITE_EXPOSE_BACKEND_ERRORS=true
```

## Build or test commands

```bash
cd /Users/will/Code/CodexProjects/DjangoStarter/backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd /Users/will/Code/CodexProjects/DjangoStarter/frontend
npm run build
```
