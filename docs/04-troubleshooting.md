# 04 Troubleshooting

Use this when local behavior does not match expected checkout or account flows.

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
await window.Clerk?.session?.getToken?.()
```

3. Retry request with `Authorization: Bearer <token>`.

## Buy button shows "Checkout URL missing"

Problem:

- `price.metadata.checkout_url` is empty
- `VITE_ENABLE_DEV_MANUAL_CHECKOUT` is false

Fix options:

1. Add a real Clerk checkout URL to the price metadata.
2. For local simulation only, set `VITE_ENABLE_DEV_MANUAL_CHECKOUT=true` and `ORDER_CONFIRM_ALLOW_MANUAL=True`.

Example metadata patch:

```bash
curl -X PATCH http://127.0.0.1:8000/api/seller/prices/PUT_PRICE_ID_HERE/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"metadata":{"checkout_url":"https://checkout.clerk.com/..."}}'
```

## Manual confirm returns `403`

Problem:

- `ORDER_CONFIRM_ALLOW_MANUAL` is `False`

Fix for local development only:

```bash
# backend/.env
ORDER_CONFIRM_ALLOW_MANUAL=True
```

Restart backend.

## Clerk direct confirm returns `409 pending_verification`

Problem:

- Direct client-side Clerk confirmation is intentionally blocked

Fix:

- Use verified Clerk webhooks
- Keep `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=False` in production

## Product does not appear in `/api/products/`

Problem:

- Product is not published
- No active price exists

Fix:

- Set `visibility` to `published`
- Make sure at least one active price exists

Quick check:

```bash
cd ./backend
source .venv/bin/activate
python3 manage.py shell -c "from api.models import Product; print(list(Product.objects.values('id','slug','visibility','active_price_id')))"
```

## Download access fails with `503`

Problem:

- Asset storage backend config is incomplete

Fix:

- Verify `ASSET_STORAGE_BACKEND`
- For `supabase`, verify `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and bucket
- For `s3`, verify endpoint, access key, secret key, and bucket

Relevant vars live in `backend/.env.example`.

## Download URL request fails with `403`

Problem:

- Download grant is expired, inactive, or out of attempts

Fix:

- Check `/api/account/downloads/` for `can_download`, `expires_at`, and `download_count`
- Issue a new fulfilled order or reset grant limits for testing

## Clerk webhook events are ignored or failing

Problem:

- Signature mismatch or wrong endpoint in Clerk dashboard

Fix:

- Webhook URL must be `/api/webhooks/clerk/`
- `CLERK_WEBHOOK_SIGNING_SECRET` must match Clerk dashboard value
- Confirm your public URL resolves to this backend

## Order or booking succeeds but no email arrives

Problem:

- `RESEND_API_KEY` or `RESEND_FROM_EMAIL` is missing
- Sender domain is not verified in Resend
- Buyer has no `billing_email` or profile `email`
- Resend rejected the request

Fix:

1. Confirm env values in `backend/.env`:

```bash
FRONTEND_APP_URL=http://127.0.0.1:5173
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=Acme <updates@yourdomain.com>
RESEND_REPLY_TO_EMAIL=support@yourdomain.com
```

2. Restart backend after env changes.
3. Confirm your sender is verified in Resend dashboard.
4. Confirm customer profile has an email:

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/api/profile/
```

5. Retry purchase or booking and check backend logs for Resend warnings.

## AI providers show as disabled in `/app`

Problem:

- AI env vars are not set for OpenRouter or Ollama placeholders.

Fix:

Set one or both in `backend/.env`:

```bash
OPENROUTER_API_KEY=or_xxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=openai/gpt-4.1-mini

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

Then restart backend and refresh `/app`.

## AI usage summary looks unrealistic

Problem:

- Starter usage values are placeholders until you wire provider telemetry.

Fix:

- Use `/api/ai/usage/summary/` as an initial contract only.
- Replace usage math with real counters from your model gateway logs or billing pipeline.
- Keep subscription state webhook-driven from Clerk.

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

## Deploy check fails

Problem:

- Missing production security config

Fix:

```bash
cd ./backend
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy
```

Address all reported errors before release.
