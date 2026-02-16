# Frontend Module Layout

The frontend is intentionally split into route modules, reusable UI components, and shared helpers so React developers can navigate it quickly.

## Entry points

- `./frontend/src/main.tsx`
- `./frontend/src/app.tsx`

## Folder architecture

- `routes`: route composition and page modules
- `components`: reusable UI building blocks
- `shared`: shared types and style helpers
- `lib`: API and app-level utility modules
- `public`: static assets copied by Vite at build time

## Core route modules

- `./frontend/src/routes/index.tsx`
- `./frontend/src/routes/public/routes.tsx`
- `./frontend/src/routes/app/routes.tsx`

## Shared component modules

- `./frontend/src/components/layout/app-shell.tsx`
- `./frontend/src/components/feedback/toast.tsx`

## Shared helper modules

- `./frontend/src/shared/types.ts`
- `./frontend/src/shared/ui-utils.ts`
- `./frontend/src/lib/api.ts`
- `./frontend/src/lib/signals.ts`

## Example-only modules

Everything non-essential for production UX lives here:

- `./frontend/src/components/examples/examples-page.tsx`
- `./frontend/src/components/examples/frontend-backend-examples.tsx`
- `./frontend/src/components/examples/signal-sandbox-example.tsx`

Route: `/examples`

## Key routes

- `/` marketing landing surface
- `/app` preflight and account dashboard
- `/products` and `/products/:slug` offer flow
- `/pricing` Clerk pricing flow
- `/account/purchases`
- `/account/subscriptions`
- `/account/downloads`
- `/account/bookings`
- `/examples`

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

## UX rules

1. Show explicit feedback for actions.
2. Do not rely on console logs for user state awareness.
3. Keep pricing data server-driven.
4. Keep all optional demos in `/examples`.
