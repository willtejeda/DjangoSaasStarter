# OpenCode Notes

Read `./AGENTS.md` first.

Default assumptions:

1. Backend is source of truth for payment and fulfillment state.
2. Verified Clerk webhooks drive production order confirmation.
3. Frontend should never self-confirm payments in production.
4. Subscription sync status endpoint is read-only by default and only refreshed explicitly with `?refresh=1`.
5. Optional demos belong in `/frontend/src/features/examples/`.
6. Preflight checks in `/app` should pass before feature branch expansion.
