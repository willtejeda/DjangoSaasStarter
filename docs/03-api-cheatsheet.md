# 03 API Cheatsheet

Base URL: `http://127.0.0.1:8000/api`

## Public endpoints

- `GET /health/`
- `GET /products/`
- `GET /products/:slug/`

## Authenticated account endpoints

- `GET /me/`
- `GET /billing/features/`
- `GET /ai/providers/`
- `POST /ai/tokens/estimate/`
- `POST /ai/chat/complete/`
- `POST /ai/images/generate/`
- `GET /ai/usage/summary/`
- `GET /supabase/profile/`
- `POST /account/preflight/email-test/`
- `GET /account/orders/`
- `POST /account/orders/create/`
- `POST /account/orders/:public_id/confirm/` (dev flags only)
- `GET /account/subscriptions/` (read-only local projection; no Clerk sync side effects)
- `GET /account/subscriptions/status/` (read-only cached status)
- `GET /account/subscriptions/status/?refresh=1` (forces a Clerk re-sync attempt)
- `GET /account/entitlements/`
- `GET /account/downloads/`
- `POST /account/downloads/:token/access/`
- `GET /account/orders/work/`
- `GET /account/bookings/` (legacy alias for `/account/orders/work/`)

## Seller endpoints

- `GET/POST /seller/products/`
- `GET/PATCH/DELETE /seller/products/:id/`
- `GET/POST /seller/products/:product_id/prices/`
- `GET/PATCH/DELETE /seller/prices/:id/`
- `GET/POST /seller/products/:product_id/assets/`
- `GET/PATCH/DELETE /seller/assets/:id/`
- `GET/PUT/PATCH /seller/products/:product_id/service-offer/`

## Webhook endpoint

- `POST /webhooks/clerk/`

## Frontend examples

### 1. Read product catalog

```ts
import { apiRequest } from './frontend/src/lib/api';

const products = await apiRequest<Array<{ id: number; slug: string; name: string }>>('/products/');
```

### 2. Create pending order

```ts
import { authedRequest } from './frontend/src/lib/api';
import { useAuth } from '@clerk/clerk-react';

const { getToken } = useAuth();

const created = await authedRequest<{
  order: { public_id: string };
  checkout?: { checkout_url?: string | null };
}>(getToken, '/account/orders/create/', {
  method: 'POST',
  body: { price_id: 12, quantity: 1 },
});
```

### 3. Read subscriptions, sync status, and usage

```ts
const syncStatus = await authedRequest(getToken, '/account/subscriptions/status/');
let subscriptions = await authedRequest(getToken, '/account/subscriptions/');

// Explicitly force a sync attempt only when needed (for example, stale badge retry):
const refreshedSync = await authedRequest(getToken, '/account/subscriptions/status/?refresh=1');
subscriptions = await authedRequest(getToken, '/account/subscriptions/');

const usage = await authedRequest(getToken, '/ai/usage/summary/');
```

### 4. Estimate tokens before submit (backend estimate)

```ts
const estimate = await authedRequest<{
  model: string;
  estimated_tokens: { total: number };
}>(getToken, '/ai/tokens/estimate/', {
  method: 'POST',
  body: {
    model: 'gpt-4.1-mini',
    messages: [{ role: 'user', content: 'Draft a launch email.' }],
  },
});
```

### 5. Run debug chat pipeline (usage enforced server-side)

```ts
const debug = await authedRequest<{
  assistant_message: string;
  usage: { total_tokens: number; cycle_tokens_remaining: number | null };
}>(getToken, '/ai/chat/complete/', {
  method: 'POST',
  body: {
    provider: 'simulator',
    model: 'gpt-4.1-mini',
    messages: [{ role: 'user', content: 'Generate a short test response.' }],
    max_output_tokens: 180,
  },
});
```

## Payment contract summary

1. Client creates pending order.
2. Clerk checkout collects payment.
3. Verified webhook confirms payment server-side.
4. Fulfillment and entitlements are created server-side.

Do not trust client-only payment confirmation in production.
