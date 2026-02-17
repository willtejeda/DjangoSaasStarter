# 05 Customize Template

Goal: keep what you need, delete what you do not.

## Product positioning first

Before coding, answer:

1. Who pays first?
2. What result do they buy?
3. What unlocks immediately after payment?

Update these first in `./frontend/src/routes/landing/page.tsx`.

## Modular delete map

### Safe to remove if unused

- Service work-order flow:
  - `/api/account/orders/work/` (`/api/account/bookings/` legacy alias)
  - `FulfillmentOrder` and `ServiceOffer` related UI routes
- Digital asset flow:
  - download grant pages and storage integration
- AI usage scaffolding:
  - `/api/ai/providers/`
  - `/api/ai/tokens/estimate/`
  - `/api/ai/chat/complete/`
  - `/api/ai/images/generate/`
  - `/api/ai/usage/summary/`

### Keep for almost every SaaS

- Order create and list endpoints
- Webhook verification and handlers
- Customer account and profile sync
- Subscription and entitlement records

## Backend module map

- Models: `./backend/api/models/`
- Views: `./backend/api/views_modules/`
- Tools: `./backend/api/tools/`
- Webhooks: `./backend/api/webhooks/`

## Frontend module map

- App shell and routes: `./frontend/src/app.tsx`
- Route map composition: `./frontend/src/routes/index.tsx`
- Landing page route: `./frontend/src/routes/landing/page.tsx`
- Pricing route: `./frontend/src/routes/pricing/page.tsx`
- Product routes: `./frontend/src/routes/products/`
- Signed-in dashboard route: `./frontend/src/routes/app/dashboard/page.tsx`
- Signed-in account routes: `./frontend/src/routes/app/account/`
- API client: `./frontend/src/lib/api.ts`
- UI utilities: `./frontend/src/shared/ui-utils.ts`
- Layout and nav components: `./frontend/src/components/layout/app-shell.tsx`
- Example-only code: `./frontend/src/routes/examples/`

## Recommended first customizations

1. Replace hero copy with your niche promise
2. Configure one digital offer and one recurring plan
3. Add your own entitlement keys
4. Replace AI usage placeholders with real provider telemetry
5. Keep frontend token preflight labeled as estimate and enforce limits on backend ledger events

## Plan tier resolution default

- Default behavior infers plan tier from Clerk billing features in token claims.
- Backend remains source of truth for usage enforcement, independent of frontend estimates.
- If your product requires stricter per-plan overrides, add explicit mapping on top of the default claim inference.

## Starter AI quota defaults

These are controlled by backend env flags and enforced server-side per usage cycle:

- `AI_USAGE_LIMIT_FREE_TOKENS=100000`
- `AI_USAGE_LIMIT_FREE_IMAGES=120`
- `AI_USAGE_LIMIT_FREE_VIDEOS=2`
- `AI_USAGE_LIMIT_PRO_TOKENS=1500000`
- `AI_USAGE_LIMIT_PRO_IMAGES=1000`
- `AI_USAGE_LIMIT_PRO_VIDEOS=40`

These defaults are tuned to common creator-tool ranges and should be adjusted to your margin targets.

## Billing sync windows

Clerk remains the billing source of truth. Django keeps a local projection and re-syncs on demand.

- `BILLING_SYNC_SOFT_STALE_SECONDS=900`
- `BILLING_SYNC_HARD_TTL_SECONDS=10800`
- `BILLING_SYNC_SOFT_WARNING_MESSAGE=...`
- `BILLING_SYNC_HARD_BLOCK_MESSAGE=...`

Recommended template defaults:

1. Keep soft stale short for UX warning visibility.
2. Keep hard TTL low enough to limit spend during provider sync outages.
3. Block usage-generating AI endpoints on hard stale, but keep read-only account pages available.
4. Keep `GET /account/subscriptions/` read-only local projection with no implicit sync side effects.
5. Keep `GET /account/subscriptions/status/` read-only; use `?refresh=1` only for explicit retries.

6. Add onboarding emails and support automations

## Add a new frontend page

1. Create the page component in either:
   - a URL-focused route folder inside `./frontend/src/routes/`, or
   - `./frontend/src/routes/app/account/` for signed-in account pages
2. Wire route matching in `./frontend/src/routes/index.tsx`.
3. Add or update sidebar links via `./frontend/src/components/layout/app-shell.tsx`.
4. Run `npm run typecheck` and `npm run build`.

## Growth checklist

1. Launch one offer with one traffic channel
2. Add testimonials and outcomes
3. Improve onboarding completion rate
4. Add upsell and retention loop
5. Expand into multi-offer catalog
