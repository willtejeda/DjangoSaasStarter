# OpenCode Notes

Read `./AGENTS.md` before coding.

Default assumptions:

1. Backend is source of truth for order status and fulfillment.
2. Verified Clerk webhooks drive payment confirmation.
3. Frontend must not self-confirm payments unless explicitly in local dev mode.
