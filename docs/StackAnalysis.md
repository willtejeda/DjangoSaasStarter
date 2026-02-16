# Stack Analysis and FAQ

## Positioning

DjangoStarter is a cashflow-first SaaS starter for Python builders.

It is optimized for one thing first: getting to trustworthy revenue quickly.

## Why this stack

### Django + DRF

- Explicit data model ownership
- Reliable migrations
- Fast API development
- Strong Python ecosystem for AI workflows

### React + Vite + Tailwind

- Fast frontend iteration
- Huge component ecosystem
- Easy UI customization without custom CSS debt

### Clerk

- Auth and billing complexity offloaded
- Production-ready account and payment surfaces
- Webhook events for server-side truth

### Supabase

- Postgres + operator tooling + realtime capabilities
- Better data operations surface than custom admin alone
- Still works with Django as schema owner

### Resend

- Clean transactional email API
- Good fit for lifecycle and marketing-adjacent sends
- Works with template workflows and tag-based observability

## New user questions answered

### Why not just use Next.js for everything?

If your core team is JS-heavy and wants one-language fullstack, Next.js is a great fit.

If your core product logic and AI workflows are Python-first, Django reduces translation overhead and keeps backend logic in the ecosystem where most AI tooling lands first.

### Why use Django migrations if Supabase has SQL editor?

Because dual schema ownership creates drift and production bugs.

Use Supabase dashboard for operations, not schema authorship of Django-managed tables.

### Is this scalable?

Yes, if you keep contracts strict:

- server-side payment truth
- migration discipline
- observability and test gates
- background task strategy when throughput grows

### Is this good for non-technical creators?

Yes, if they use the preflight system and focus on one paid loop first.

This starter reduces the risky plumbing so they can focus on offer quality and distribution.

## First dollar playbook

1. Launch one focused offer.
2. Set up one paid traffic or distribution channel.
3. Capture buyer feedback fast.
4. Improve conversion and onboarding.
5. Add recurring plan only after proof.

## Domain and email basics

1. Buy a domain.
2. Set DNS for app and email sender.
3. Verify sender domain in Resend.
4. Route support inbox with one business address.
5. Use tagged transactional events for visibility.

## What to do right after clone

1. Run quickstart
2. Pass `/app` preflight checks
3. Create one product and one price
4. Complete one paid checkout
5. Verify fulfillment
6. Only then start custom features
