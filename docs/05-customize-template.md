# 05 Customize Template Into Your SaaS

Goal: convert the starter into your product without breaking payment truth or fulfillment.

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
- Entry offer: $49 one time toolkit
- Upgrade: $29/month accountability subscription

## 2. Update messaging before backend changes

Start in `frontend/src/app.tsx`.

Update at minimum:

- Hero headline and subheadline
- CTA labels
- Offer cards and benefits
- Pricing support copy

A first-time visitor should understand who this is for, what outcome it creates, and why they should buy now.

## 3. Model catalog and pricing from seller APIs

Create:

- One entry offer (`one_time`)
- One recurring plan (`monthly` or `yearly`)
- Feature keys for entitlement checks

Do not hardcode prices in frontend. Keep catalog source of truth server-side.

For each buyable price, set `metadata.checkout_url` to your Clerk checkout URL.

## 4. Configure fulfillment paths

Digital products:

- Attach one or more `DigitalAsset` records
- Validate download grants are created after fulfillment

Service products:

- Upsert `ServiceOffer` for each service product
- Validate bookings can be created from account routes

## 5. Keep payment truth server-side

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

## 6. Validate signed-in account UX

Test these paths with both empty and populated data:

- `/app`
- `/account/purchases`
- `/account/subscriptions`
- `/account/downloads`
- `/account/bookings`

Fix any console errors before deployment.

## 7. Ship only after quality gates pass

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ./frontend
npm run build
```

## 8. Track launch metrics from day one

Track weekly:

- Product page visitors
- Checkout starts
- Checkout completion rate
- Refund rate
- Active subscriptions
- Revenue by offer

Starter benchmark target:

- 500 visitors/week
- 4 percent checkout starts
- 30 percent checkout completion
- 6 paid customers/week

Tune offer, price, and onboarding copy based on these numbers.
