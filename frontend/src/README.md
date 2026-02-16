# Frontend Module Layout

The frontend is designed for fast customization with minimal frontend expertise.

## Entry points

- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/main.tsx`
- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/app.tsx`

## Core app modules

- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/lib/api.ts`
- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/lib/signals.ts`
- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/app-shell/types.ts`
- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/app-shell/ui-utils.ts`
- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/app-shell/toast.tsx`

## Example-only modules

Everything non-essential for production UX lives here:

- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/examples/examples-page.tsx`
- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/examples/frontend-backend-examples.tsx`
- `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/examples/signal-sandbox-example.tsx`

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
