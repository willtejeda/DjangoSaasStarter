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
- `GET /ai/usage/summary/`
- `GET /supabase/profile/`
- `POST /account/preflight/email-test/`
- `GET /account/orders/`
- `POST /account/orders/create/`
- `POST /account/orders/:public_id/confirm/` (dev flags only)
- `GET /account/subscriptions/`
- `GET /account/entitlements/`
- `GET /account/downloads/`
- `POST /account/downloads/:token/access/`
- `GET /account/bookings/`
- `POST /account/bookings/`

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

### 3. Read subscriptions and usage

```ts
const [subscriptions, usage] = await Promise.all([
  authedRequest(getToken, '/account/subscriptions/'),
  authedRequest(getToken, '/ai/usage/summary/'),
]);
```

## Payment contract summary

1. Client creates pending order.
2. Clerk checkout collects payment.
3. Verified webhook confirms payment server-side.
4. Fulfillment and entitlements are created server-side.

Do not trust client-only payment confirmation in production.
