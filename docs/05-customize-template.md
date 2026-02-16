# 05 Customize Template Into Your SaaS

Goal: convert the starter into your product without breaking payment truth, fulfillment trust, or schema ownership.

Before feature work, run preflight checks from `/app` and make sure all integration tests are passing.

## 1. Lock the paid outcome first

Write these 5 lines before coding:

1. Who is the buyer?
2. What painful problem are they paying to fix?
3. What measurable result do they get in 7 days?
4. What is your entry price?
5. What is your upgrade path?

Example:

- Buyer: Solo creator with inconsistent publishing
- Problem: Missed deadlines and no repeatable workflow
- 7 day result: Publish 3 quality videos with one system
- Entry offer: $49 one-time toolkit
- Upgrade: $29/month AI-assisted accountability subscription

## 2. Update messaging before backend changes

Start in `frontend/src/app.tsx`.

Update at minimum:

- Hero headline and subheadline
- CTA labels
- Offer cards and benefits
- Pricing support copy

A first-time visitor should understand who this is for, what outcome it creates, and why they should buy now.

## 3. Keep schema ownership strict

Django owns schema. Supabase is operations and hosting.

Required:

- Use Django models and migrations for schema changes
- Run `makemigrations` and `migrate` for every schema update

Avoid direct schema edits in Supabase dashboard for Django-managed tables.

## 4. Model catalog and pricing from seller APIs

Create:

- One entry offer (`one_time`)
- One recurring plan (`monthly` or `yearly`)
- Feature keys for entitlement checks

Do not hardcode prices in frontend. Keep catalog source of truth server-side.

For each buyable price, set `metadata.checkout_url` to your Clerk checkout URL.

## 4.1 Configure Clerk Billing for subscriptions

In Clerk dashboard:

1. Enable Billing and connect Stripe.
2. Create Plans and attach feature entitlements.
3. Keep plan names aligned with your Django `Price` records.
4. Use `PricingTable` in frontend for buyer plan selection.

Webhook events to enable at minimum:

- `subscription.created`
- `subscription.updated`
- `subscription.active`
- `subscription.pastDue`
- `subscription.canceled`
- `paymentAttempt.created`
- `paymentAttempt.updated`
- `checkout.created`
- `checkout.updated`

Endpoint:

- `POST /api/webhooks/clerk/`

## 5. Configure fulfillment paths

Digital products:

- Attach one or more `DigitalAsset` records
- Validate download grants are created after fulfillment

Service products:

- Upsert `ServiceOffer` for each service product
- Validate bookings can be created from account routes

## 6. Configure AI subscription scaffolding

Use recurring plans plus usage surfaces for AI products:

- Define feature keys such as `ai_chat`, `ai_images`, `ai_video`
- Configure at least one provider placeholder (`OPENROUTER_*` or `OLLAMA_*`)
- Validate `/api/ai/providers/` and `/api/ai/usage/summary/`

These usage values are starter placeholders until your provider telemetry is connected.

## 7. Configure transactional email

Use Resend for buyer lifecycle communication.

Required env in `backend/.env`:

- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`

Recommended:

- `FRONTEND_APP_URL` so email deep links route to your app
- `RESEND_REPLY_TO_EMAIL` for support and replies

Implemented sends:

- Order fulfillment confirmation
- Booking request confirmation

Delivery is best-effort and should never block checkout or booking creation.

## 8. Keep payment truth server-side

Required production behavior:

1. `POST /api/account/orders/create/` creates `pending_payment` orders.
2. Clerk checkout handles payment.
3. Verified Clerk webhooks mark local orders paid.
4. Fulfillment runs only after verified payment state.

Local-only flags:

- `ORDER_CONFIRM_ALLOW_MANUAL`
- `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM`
- `VITE_ENABLE_DEV_MANUAL_CHECKOUT`

Keep all three disabled in production.

## 9. Validate signed-in account UX

Test these paths with both empty and populated data:

- `/app`
- `/account/purchases`
- `/account/subscriptions`
- `/account/downloads`
- `/account/bookings`

Fix any console errors before deployment.

## 10. Validate outbound email behavior

Before launch, verify both events in a staging-like environment:

1. Complete one paid order and confirm fulfillment email send in Resend.
2. Create one booking request and confirm booking email send in Resend.

## 11. Ship only after quality gates pass

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ./frontend
npm run build
```

## 12. Track launch metrics from day one

Track weekly:

- Product page visitors
- Checkout starts
- Checkout completion rate
- Refund rate
- Active subscriptions
- Revenue by offer
- Usage-to-upgrade conversion for AI plans

Starter benchmark target:

- 500 visitors/week
- 4 percent checkout starts
- 30 percent checkout completion
- 6 paid customers/week

Tune offer, price, and onboarding copy based on these numbers.
