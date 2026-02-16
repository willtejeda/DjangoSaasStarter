# 05 Customize Template

Goal: keep what you need, delete what you do not.

## Product positioning first

Before coding, answer:

1. Who pays first?
2. What result do they buy?
3. What unlocks immediately after payment?

Update these first in `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/app.tsx`.

## Modular delete map

### Safe to remove if unused

- Service booking flow:
  - `/api/account/bookings/`
  - `Booking` and `ServiceOffer` related UI routes
- Digital asset flow:
  - download grant pages and storage integration
- AI usage scaffolding:
  - `/api/ai/providers/`
  - `/api/ai/usage/summary/`

### Keep for almost every SaaS

- Order create and list endpoints
- Webhook verification and handlers
- Customer account and profile sync
- Subscription and entitlement records

## Backend module map

- Models: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/models/`
- Views: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/views_modules/`
- Tools: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/tools/`
- Webhooks: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/webhooks/`

## Frontend module map

- App shell and routes: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/app.tsx`
- API client: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/lib/api.ts`
- UI utilities: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/app-shell/ui-utils.ts`
- Example-only code: `/Users/will/Code/CodexProjects/DjangoStarter/frontend/src/features/examples/`

## Recommended first customizations

1. Replace hero copy with your niche promise
2. Configure one digital offer and one recurring plan
3. Add your own entitlement keys
4. Replace AI usage placeholders with real provider telemetry
5. Add onboarding emails and support automations

## Growth checklist

1. Launch one offer with one traffic channel
2. Add testimonials and outcomes
3. Improve onboarding completion rate
4. Add upsell and retention loop
5. Expand into multi-offer catalog
