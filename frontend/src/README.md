# Frontend Module Layout

The frontend is structured for fast onboarding by both humans and coding agents:

- `routes/*` follows URL hierarchy
- `components/*` contains reusable UI primitives
- `shared/*` contains cross-route types and helpers

## Entry points

- `./frontend/src/main.tsx`
- `./frontend/src/app.tsx`

## Folder architecture

- `routes`: URL-first route modules and route-specific sections
- `components`: reusable cross-route UI (layout shell, feedback, primitives)
- `shared`: shared types and style helpers
- `lib`: API and app-level utility modules
- `./frontend/public/`: static assets copied by Vite at build time

## Route hierarchy (URL aligned)

- `/` -> `./frontend/src/routes/landing/page.tsx`
- `/pricing` -> `./frontend/src/routes/pricing/page.tsx`
- `/products` -> `./frontend/src/routes/products/catalog-page.tsx`
- `/products/:slug` -> `./frontend/src/routes/products/detail-page.tsx`
- `/checkout/success` and `/checkout/cancel` -> `./frontend/src/routes/checkout/state-page.tsx`
- `/app` -> `./frontend/src/routes/app/dashboard/page.tsx`
- `/account/purchases` -> `./frontend/src/routes/app/account/purchases-page.tsx`
- `/account/subscriptions` -> `./frontend/src/routes/app/account/subscriptions-page.tsx`
- `/account/downloads` -> `./frontend/src/routes/app/account/downloads-page.tsx`
- `/account/orders/work` -> `./frontend/src/routes/app/account/bookings-page.tsx`
- `/account/bookings` (legacy alias) -> `./frontend/src/routes/app/account/bookings-page.tsx`
- `/examples` -> `./frontend/src/routes/examples/page.tsx`

`./frontend/src/routes/index.tsx` owns app-level route matching and shell composition.

## Reusable components

- Layout shell and navigation: `./frontend/src/components/layout/app-shell.tsx`
- Toast notifications and feedback: `./frontend/src/components/feedback/toast.tsx`

## Layout and navigation behavior

- Desktop (`lg` and up):
  - Left sidebar is pinned in a dedicated rail.
  - All primary navigation links live in the sidebar.
  - Theme/auth controls live in the sidebar.
- Mobile and tablet (`< lg`):
  - Sidebar opens as a drawer using a simple `Menu` button.
  - Route change closes the drawer automatically.
- Contract:
  - One navigation source of truth: sidebar content.
  - No duplicate top navbar navigation.

## Shared helper modules

- `./frontend/src/shared/types.ts`
- `./frontend/src/shared/ui-utils.ts`
- `./frontend/src/shared/token-estimator.ts`
- `./frontend/src/lib/api.ts`
- `./frontend/src/lib/signals.ts`

## Frontend to backend examples

### Read public offers

```ts
const offers = await apiRequest('/products/');
```

### Create pending order

```ts
const pending = await authedRequest(getToken, '/account/orders/create/', {
  method: 'POST',
  body: { price_id: 12, quantity: 1 },
});
```

### Read usage summary

```ts
const usage = await authedRequest(getToken, '/ai/usage/summary/');
```

### Read billing sync status (cached)

```ts
const syncStatus = await authedRequest(getToken, '/account/subscriptions/status/');
```

### Read subscriptions (local projection only)

```ts
const subscriptions = await authedRequest(getToken, '/account/subscriptions/');
```

### Retry billing sync only when stale

```ts
const refreshed = await authedRequest(getToken, '/account/subscriptions/status/?refresh=1');
```

### Run debug AI flow (simulator mode)

```ts
const debug = await authedRequest(getToken, '/ai/chat/complete/', {
  method: 'POST',
  body: {
    provider: 'simulator',
    model: 'gpt-4.1-mini',
    messages: [{ role: 'user', content: 'Generate a test response.' }],
  },
});
```

### Frontend token preflight estimate

```ts
import { countChatTokensEstimate } from './frontend/src/shared/token-estimator';

const estimated = await countChatTokensEstimate([{ role: 'user', content: 'My prompt' }], 'gpt-4.1-mini');
```

Use this estimate for UX only. Backend usage events and limits remain authoritative.

## UX rules

1. Show explicit feedback for async actions.
2. Do not rely on console logs for user state awareness.
3. Keep pricing data server-driven.
4. Keep optional demos under `routes/examples/*`.
5. Keep navigation singular per breakpoint: sidebar rail on desktop, sidebar drawer on mobile.
6. Keep navigation definitions in one place inside `components/layout/app-shell.tsx`.
