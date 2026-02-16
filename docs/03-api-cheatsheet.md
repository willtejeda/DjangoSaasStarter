# 03 API Cheatsheet

Goal: copy and paste the most-used API calls.

## 1. Set local variables

```bash
export API=http://127.0.0.1:8000/api
export TOKEN="paste_clerk_jwt_here"
```

Quick browser token grab after sign in:

```js
await window.Clerk?.session?.getToken?.()
```

If this returns `undefined`, use your app code path with Clerk `useAuth().getToken()` and paste that token.

## 2. Public endpoints

Health:

```bash
curl "$API/health/"
```

Public catalog:

```bash
curl "$API/products/"
```

Public product detail:

```bash
curl "$API/products/focus-sprint-kit/"
```

## 3. Auth and profile endpoints

Current user envelope:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/me/"
```

Profile model:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/profile/"
```

Clerk user profile passthrough:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/me/clerk/"
```

Feature checks:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/billing/features/"
curl -H "Authorization: Bearer $TOKEN" "$API/billing/features/?feature=workflow_os"
```

AI provider and usage placeholders:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/ai/providers/"
curl -H "Authorization: Bearer $TOKEN" "$API/ai/usage/summary/"
```

## 4. Project endpoints

Create project:

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

Update project with id `1`:

```bash
curl -X PATCH "$API/projects/1/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"live"}'
```

## 5. Buyer account endpoints

Get customer billing profile:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/customer/"
```

Patch customer profile:

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

Send a preflight Resend test email:

```bash
curl -X POST "$API/account/preflight/email-test/" \
  -H "Authorization: Bearer $TOKEN"
```

List orders:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/orders/"
```

Manual confirm for local development only:

```bash
curl -X POST "$API/account/orders/PUT_ORDER_PUBLIC_ID_HERE/confirm/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "manual",
    "external_id": "manual_123"
  }'
```

List subscriptions:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/subscriptions/"
```

List entitlements:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/account/entitlements/"
curl -H "Authorization: Bearer $TOKEN" "$API/account/entitlements/?current=false"
```

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

## 6. Seller endpoints

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

Get seller product `42`:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/seller/products/42/"
```

Patch seller product `42`:

```bash
curl -X PATCH "$API/seller/products/42/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tagline":"Ship faster with one execution system"}'
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
      "checkout_url": "https://checkout.clerk.com/..."
    }
  }'
```

Patch price `99` to update checkout URL metadata:

```bash
curl -X PATCH "$API/seller/prices/99/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "checkout_url": "https://checkout.clerk.com/..."
    }
  }'
```

Create digital asset for product `42`:

```bash
curl -X POST "$API/seller/products/42/assets/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Workflow OS ZIP",
    "file_path": "products/workflow-os-v1.zip",
    "version_label": "v1",
    "is_active": true
  }'
```

Upsert service offer for service product `77`:

```bash
curl -X PUT "$API/seller/products/77/service-offer/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_minutes": 45,
    "delivery_days": 3,
    "revision_count": 1,
    "onboarding_instructions": "Send goals and blockers before the session."
  }'
```

## 7. Other integration endpoints

Supabase profile probe:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API/supabase/profile/"
```

Success payload:

```json
{
  "ok": true,
  "detail": "Supabase profile probe succeeded.",
  "profile": {
    "id": 1,
    "clerk_user_id": "user_123"
  }
}
```

Soft-failure payload (still HTTP 200 so dashboards can keep loading):

```json
{
  "ok": false,
  "detail": "Supabase probe failed. Check SUPABASE_URL and API keys.",
  "error": "SUPABASE_URL is not configured."
}
```

Clerk webhook receiver:

```text
POST /api/webhooks/clerk/
```

## 8. AI scaffolding notes

- `/api/ai/providers/` is env-driven and reports OpenRouter and Ollama placeholder readiness.
- `/api/ai/usage/summary/` returns starter usage buckets for tokens, images, and videos.
- Replace placeholder usage math with real telemetry when integrating production model calls.

Production rule: do not fake webhook confirmations. Use Clerk webhook delivery with valid `CLERK_WEBHOOK_SIGNING_SECRET`.

## 9. Resend transactional email behavior

Email sends are triggered by backend workflows, not direct email endpoints:

- Order fulfillment sends a confirmation email after payment is verified and the order is fulfilled.
- Booking creation sends a booking confirmation email.

Relevant API calls that can trigger these flows:

- `POST /api/account/orders/create/` then payment verification and fulfillment
- `POST /api/account/orders/<public_id>/confirm/` for local manual flow only
- `POST /api/account/bookings/`

Required env for send attempts:

- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`

Optional but recommended:

- `FRONTEND_APP_URL` for email deep links
- `RESEND_REPLY_TO_EMAIL`

Important: delivery is best-effort and does not block checkout or booking creation.

## 10. Frontend integration snippets (React + Clerk)

Use these patterns from `frontend/src/lib/api.ts`:

```ts
import { apiRequest, authedRequest } from './lib/api';
```

Public pricing catalog:

```ts
const products = await apiRequest<Array<{
  id: number;
  slug: string;
  name: string;
  active_price?: { amount_cents: number; currency: string } | null;
}>>('/products/');
```

Create order for selected price:

```ts
const orderPayload = await authedRequest<{
  order: { public_id: string };
  checkout?: { checkout_url?: string | null };
}>(getToken, '/account/orders/create/', {
  method: 'POST',
  body: { price_id: selectedPriceId, quantity: 1 },
});
```

Load subscriptions and usage:

```ts
const [subs, usage] = await Promise.all([
  authedRequest(getToken, '/account/subscriptions/'),
  authedRequest(getToken, '/ai/usage/summary/'),
]);
```
