# 04 Troubleshooting

Use this when something looks broken locally.

## Frontend says "Missing Clerk config"

Problem:

- `VITE_CLERK_PUBLISHABLE_KEY` is missing in `frontend/.env`

Fix:

```bash
cd ./frontend
cp .env.example .env
# set VITE_CLERK_PUBLISHABLE_KEY
npm run dev
```

## `401 Unauthorized` from protected API routes

Problem:

- Missing or invalid Clerk JWT

Fix:

1. Sign in on frontend.
2. Get a fresh token:

```js
await window.Clerk.session.getToken()
```

3. Retry request with `Authorization: Bearer <token>`.

## Manual confirm request returns `403`

Problem:

- `ORDER_CONFIRM_ALLOW_MANUAL` is `False`

Fix for local development only:

```bash
# backend/.env
ORDER_CONFIRM_ALLOW_MANUAL=True
```

Restart backend.

## Clerk confirm request returns `409 pending_verification`

Problem:

- Direct client-side Clerk confirmation is intentionally blocked

Fix:

- Use verified Clerk webhooks
- Keep `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=False` in production

## Product does not appear in `/api/products/`

Problem:

- Product is not published

Fix:

- Set `visibility` to `published`
- Make sure at least one active price exists

Quick check in shell:

```bash
cd ./backend
source .venv/bin/activate
python3 manage.py shell -c "from api.models import Product; print(list(Product.objects.values('id','slug','visibility')))"
```

## Download URL request fails

Problem:

- Asset storage is not configured, or grant has no attempts left

Fix:

- Verify storage env vars in `backend/.env`
- Verify `ASSET_STORAGE_BACKEND`, bucket, and credentials
- Check grant state in `/api/account/downloads/`

## Clerk webhook events are ignored or failing

Problem:

- Signature mismatch or wrong endpoint in Clerk dashboard

Fix:

- Clerk webhook URL must be `/api/webhooks/clerk/`
- `CLERK_WEBHOOK_SIGNING_SECRET` must match Clerk dashboard value
- Confirm your public URL resolves to this backend

## CORS errors in browser

Problem:

- Frontend origin is not allowed

Fix:

Set in `backend/.env`:

```bash
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Restart backend.

## Deployment safety check fails

Problem:

- Missing production security config

Fix:

```bash
cd ./backend
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy
```

Address all reported errors before release.
