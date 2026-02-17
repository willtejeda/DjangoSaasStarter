# 12 Frontend Starter Blueprint

Goal: make the frontend obvious for beginners and coding agents.

## UX-first structure rule

- `routes/*` is URL-shaped page code.
- `components/*` is reusable UI primitives only.
- `shared/*` is cross-route contracts and helpers.

If a file maps to a URL, keep it in `routes`.
If a file is reused across multiple routes, keep it in `components`.

## Default route hierarchy

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

Main route matcher:

- `./frontend/src/routes/index.tsx`

## Default reusable components (ship by default)

### Layout and navigation

- `./frontend/src/components/layout/app-shell.tsx`
- What it owns:
  - Sidebar content, page intro, status pills, metric cards
  - Desktop left-rail navigation
  - Mobile hamburger-triggered drawer using the same sidebar content

### Feedback and state affordances

- `./frontend/src/components/feedback/toast.tsx`
- What it owns:
  - Success, warning, and error toasts for async actions

### Shared contracts and helpers

- `./frontend/src/shared/types.ts`
- `./frontend/src/shared/ui-utils.ts`
- `./frontend/src/lib/api.ts`

## Starter page blocks to keep

These are good defaults for most SaaS projects:

1. Landing page blocks
- Hero and value proposition
- Proof and trust block
- Offer/tutorial block
- CTA footer block

2. Revenue route blocks
- Pricing table page
- Product catalog page
- Product detail and checkout trigger page
- Checkout result page

3. Account route blocks
- Purchases page
- Subscriptions page
- Downloads page
- Work Orders page

4. Operator dashboard blocks
- Preflight integration checklist
- KPI and status cards
- Recent activity panel
- AI usage and entitlement panel

## Developer ergonomics for agents

When prompting an agent, use route-level intent:

- "Replace landing copy" -> `routes/landing/page.tsx`
- "Add new account tab" -> `routes/app/account/*` and `routes/index.tsx`
- "Change mobile nav behavior" -> `components/layout/app-shell.tsx`
- "Add new paid offer flow" -> `routes/products/*` plus backend endpoints

## Add a new route checklist

1. Create route file in URL-aligned folder under `routes/`.
2. Add route selection logic in `./frontend/src/routes/index.tsx`.
3. Add nav link in `./frontend/src/components/layout/app-shell.tsx` if needed.
4. Keep data contracts in `./frontend/src/shared/types.ts`.
5. Run `npm run typecheck && npm run build`.
