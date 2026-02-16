# 03 API Cheatsheet

Goal: give developers copy-paste calls for the most used endpoints.

## 1. Set your local variables

```bash
export API=http://127.0.0.1:8000/api
export TOKEN="paste_clerk_jwt_here"
```

Quick way to grab a token in browser console after sign-in:

```js
await window.Clerk.session.getToken()
```

## 2. Public endpoints

Health:

```bash
curl "$API/health/"
```

Catalog:

```bash
curl "$API/products/"
```

Product detail:

```bash
curl "$API/products/focus-sprint-kit/"
```

## 3. Signed-in user endpoints

Who am I:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/me/"
```

Billing features:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/billing/features/"
```

Create a project:

```bash
curl -X POST "$API/projects/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q2 Offer Sprint",
    "summary": "Build and launch one paid offer",
    "status": "building",
    "monthly_recurring_revenue": "0.00"
  }'
```

List projects:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/projects/"
```

Update customer billing profile:

```bash
curl -X PATCH "$API/account/customer/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ava Buyer",
    "company_name": "Ava Labs",
    "country": "US"
  }'
```

## 4. Seller endpoints

Create product:

```bash
curl -X POST "$API/seller/products/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Creator Workflow OS",
    "tagline": "Run content like a system",
    "description": "Templates and SOPs for weekly publishing.",
    "product_type": "digital",
    "visibility": "published",
    "feature_keys": ["workflow_os"]
  }'
```

Create price for product `42`:

```bash
curl -X POST "$API/seller/products/42/prices/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "One-time",
    "amount_cents": 4900,
    "currency": "USD",
    "billing_period": "one_time",
    "is_active": true,
    "is_default": true,
    "metadata": {
      "checkout_url": ""
    }
  }'
```

Create service offer for service product `77`:

```bash
curl -X PUT "$API/seller/products/77/service-offer/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_minutes": 45,
    "delivery_days": 3,
    "revision_count": 1,
    "onboarding_instructions": "Send goals and current blockers before session."
  }'
```

## 5. Checkout and fulfillment endpoints

Create order with `price_id=5`:

```bash
curl -X POST "$API/account/orders/create/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": 5,
    "quantity": 1,
    "notes": "First purchase"
  }'
```

Manually confirm order in local dev only:

```bash
curl -X POST "$API/account/orders/PUT_ORDER_PUBLIC_ID_HERE/confirm/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "manual",
    "external_id": "manual_123"
  }'
```

List orders:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/orders/"
```

List subscriptions:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/subscriptions/"
```

List entitlements:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/entitlements/"
```

## 6. Downloads and bookings

List download grants:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/downloads/"
```

Request signed download URL:

```bash
curl -X POST "$API/account/downloads/PUT_DOWNLOAD_TOKEN_HERE/access/" \
  -H "Authorization: Bearer $TOKEN"
```

List bookings:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/bookings/"
```

Create booking request:

```bash
curl -X POST "$API/account/bookings/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "service_offer": 3,
    "customer_notes": "Need help fixing onboarding conversion."
  }'
```

## 7. Webhooks

Webhook URL:

```text
POST /api/webhooks/clerk/
```

Do not fake this in production. Use Clerk webhook delivery with a valid `CLERK_WEBHOOK_SIGNING_SECRET`.
