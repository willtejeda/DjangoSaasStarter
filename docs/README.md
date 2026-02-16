# DjangoStarter Docs

Use this folder as the operator manual for shipping a paid MVP from this template.

Read these docs in order:

1. `01-quickstart.md`
2. `02-first-revenue-loop.md`
3. `03-api-cheatsheet.md`
4. `04-troubleshooting.md`
5. `05-customize-template.md`
6. `StackAnalysis.md` for architecture context and tradeoffs

## What this covers

- Local backend and frontend setup
- Product, pricing, checkout, and fulfillment flow
- API endpoints for buyer and seller operations
- Common failure modes and fast fixes
- A repeatable sequence for converting the template into your SaaS

## Fast links

- Root guide: `README.md`
- Backend env reference: `backend/.env.example`
- Frontend env reference: `frontend/.env.example`
- Deployment checks: `.github/workflows/ci.yml`

## Non negotiable production rules

- Keep `DJANGO_DEBUG=False`
- Keep `ORDER_CONFIRM_ALLOW_MANUAL=False`
- Keep `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=False`
- Confirm payments from verified Clerk webhooks only
