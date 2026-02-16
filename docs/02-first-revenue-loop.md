# 02 First Revenue Loop

Goal: prove one paid loop works end to end.

## Outcome to target

A buyer can:

1. Visit offer page
2. Start checkout
3. Pay through Clerk
4. Receive fulfillment (download, subscription access, or booking)
5. See records in account pages

## Phase A: Do this before starting feature work

Use `/app` preflight and pass all checks:

1. Clerk auth and profile sync
2. Supabase bridge probe
3. Resend test email
4. Order placement test
5. Webhook payment confirmation
6. Subscription plus usage test

If any step fails, stop and fix infra.

## Phase B: Configure your first offer in Django

Use seller APIs (or admin shell) to create:

1. Product (`digital` or `service`)
2. Price (one-time or recurring)
3. Active price link
4. Feature keys for entitlement gating

Important: pricing values should come from backend payloads. Do not hardcode prices in frontend.

## Phase C: Connect Clerk billing metadata

Map your Clerk plan or checkout to product pricing in your backend metadata flow.

Checklist:

1. Plan exists in Clerk Billing
2. Price and period match your Django price
3. Checkout metadata allows backend reconciliation
4. Webhooks are configured and signed

Clerk setup order:

1. Create plan and price in Clerk Billing.
2. Ensure plan period matches your Django `Price.billing_period`.
3. Use Clerk pricing UI (`/pricing`) to validate plan visibility.
4. Use signed webhook events to sync paid state into Django.

## Phase D: Run order placement test

1. Open `/products`
2. Open one offer detail
3. Click buy to create pending order via `POST /api/account/orders/create/`
4. Complete checkout

Expected result:

- Order moves from `pending_payment` to `paid` or `fulfilled`
- State transition is server-side

## Phase E: Validate fulfillment path

Digital product flow:

1. Paid order creates download grants
2. `/account/downloads` shows grant
3. Access URL generation works

Subscription flow:

1. Recurring plan appears in `/account/subscriptions`
2. Entitlements are populated
3. `/api/ai/usage/summary/` returns usage buckets

Service flow:

1. Paid order creates booking records
2. `/account/bookings` shows request

## Phase F: Verify email touchpoints

1. Send preflight email from `/app`
2. Trigger order fulfillment and booking messages
3. Confirm recipients and sender domain are valid

## Guardrails

- Production fulfillment should rely on verified Clerk webhook events
- Keep manual confirmation flags disabled in production
- Use Django migrations only for schema changes

## Common first monetization playbook

1. Sell one small digital offer first ($29 to $99)
2. Add recurring plan after initial demand proof
3. Bundle support or service upsell
4. Improve onboarding before adding complex features
