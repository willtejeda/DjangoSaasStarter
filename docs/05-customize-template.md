# 05 Customize Template Into Your SaaS

Goal: convert the starter into your actual product in a focused sequence.

## 1. Lock your offer before coding

Write these 5 lines first:

1. Who is the buyer?
2. What painful problem are they paying to fix?
3. What result do they get in 7 days?
4. What is the starter offer price?
5. What is the upgrade path?

Example:

- Buyer: Solo creator with inconsistent publishing
- Problem: Missed deadlines and no repeatable workflow
- 7 day result: Publish 3 quality videos with one system
- Starter offer: $49 one-time toolkit
- Upgrade: $29/month accountability subscription

## 2. Update conversion copy in frontend

Start in:

- `frontend/src/app.tsx`

Update:

- Hero headline
- Subheadline
- CTA button labels
- Proof bullets
- Pricing page context text

Keep copy specific and outcome-driven.

## 3. Model your products and prices

Use seller APIs or Django admin to create:

- One entry offer (`one_time`)
- One recurring plan (`monthly` or `yearly`)
- Feature keys that map to access

Example feature keys:

- `starter_templates`
- `weekly_review`
- `private_community`

## 4. Decide fulfillment path per product type

Use `digital` when buyer should download assets.

Use `service` when buyer should request delivery or calls.

Service products should have a service offer:

- `session_minutes`
- `delivery_days`
- `revision_count`
- `onboarding_instructions`

## 5. Connect billing truth to webhooks

Required production rule:

- Payment confirmation comes from verified Clerk webhooks

Checklist:

1. Set `CLERK_WEBHOOK_SIGNING_SECRET`
2. Point Clerk webhook URL to `/api/webhooks/clerk/`
3. Keep manual confirmation flags off in production

## 6. Define success metrics before launch

Track weekly:

- Visitors to product pages
- Checkout start rate
- Paid conversion rate
- Refund rate
- Active subscribers
- Revenue by offer

Simple target example:

- 500 visitors/week
- 4 percent checkout start
- 30 percent checkout completion
- 6 paid customers/week

## 7. Ship with this minimum quality bar

```bash
cd ./backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ./frontend
npm run build
```

If all pass, you are ready for staging deployment.
