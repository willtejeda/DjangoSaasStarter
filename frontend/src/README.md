# Frontend Module Layout

`src/` is organized so product work can scale without turning `app.tsx` into the only source of truth.

## Entry points

- `main.tsx`: app bootstrap and providers.
- `app.tsx`: page composition and route-level wiring.

## Shared libraries

- `lib/api.ts`: API wrappers (`apiRequest`, `authedRequest`) and base URL helper.
- `lib/signals.ts`: lightweight app-wide signals and theme state.

## Feature modules

- `features/app-shell/types.ts`: typed API payloads and shared view-model contracts.
- `features/app-shell/ui-utils.ts`: shared UI classes and formatting helpers.

## Frontend to backend examples

### 1. Load public pricing catalog

```ts
import { apiRequest } from './lib/api';

type Product = {
  id: number;
  slug: string;
  name: string;
  active_price?: { amount_cents: number; currency: string } | null;
};

const products = await apiRequest<Product[]>('/products/');
```

### 2. Create an order from a selected price

```ts
import { authedRequest } from './lib/api';
import { useAuth } from '@clerk/clerk-react';

const { getToken } = useAuth();

const payload = await authedRequest<{
  order: { public_id: string };
  checkout?: { checkout_url?: string | null };
}>(getToken, '/account/orders/create/', {
  method: 'POST',
  body: { price_id: 12, quantity: 1 },
});

if (payload.checkout?.checkout_url) {
  window.location.href = payload.checkout.checkout_url;
}
```

### 3. Read account subscriptions and feature flags

```ts
import { authedRequest } from './lib/api';

const [subscriptions, billing] = await Promise.all([
  authedRequest<Array<{ id: number; status: string; product_name?: string }>>(getToken, '/account/subscriptions/'),
  authedRequest<{ enabled_features: string[] }>(getToken, '/billing/features/'),
]);

const hasAiFeature = billing.enabled_features.includes('ai_coach');
```

### 4. Read AI usage buckets for subscription UX

```ts
const usage = await authedRequest<{
  plan_tier: string;
  buckets: Array<{ key: string; used: number; limit: number | null }>;
}>(getToken, '/ai/usage/summary/');

const tokenBucket = usage.buckets.find((b) => b.key === 'tokens');
```

## Change rules

1. Add shared types and helpers under `features/` before adding more local duplicates.
2. Keep `app.tsx` focused on composition. Extract sections once behavior starts repeating.
3. Do not hardcode pricing data in UI. Use API payloads from `/products/` and `/seller/*` flows.
