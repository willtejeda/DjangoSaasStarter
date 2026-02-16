---
name: revenue-loop-audit
description: Use when validating the paid path from product pricing to order fulfillment and account access.
---

# Revenue Loop Audit

## Workflow

1. Verify published catalog data from `/api/products/`.
2. Create a test order via `/api/account/orders/create/`.
3. Confirm payment only through webhook or approved local dev flow.
4. Validate fulfillment artifacts:
   - entitlements
   - download grants or subscription state
5. Validate signed-in routes:
   - `/account/purchases`
   - `/account/subscriptions`
   - `/account/downloads`

## Output contract

Return:

- endpoints tested
- pass or fail per step
- root cause for each failure
- exact commands used

## Validation

- `cd backend && python3 manage.py test api -v2 --noinput`
- `cd backend && python3 manage.py check --deploy`
