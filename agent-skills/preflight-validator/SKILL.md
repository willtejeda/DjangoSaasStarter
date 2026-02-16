---
name: preflight-validator
description: Use before major feature work to verify integrations are healthy from signed-in dashboard flow.
---

# Preflight Validator

## Workflow

1. Check signed-in dashboard loads `/app` without console errors.
2. Verify integration probes:
   - Clerk profile sync
   - Supabase probe
   - Resend preflight email endpoint
3. Verify commerce probes:
   - order placement path
   - webhook confirmation path
   - subscription and usage summary path

## Output contract

Return a checklist with:

- check name
- pass or fail
- evidence link or command
- fix recommendation if failed

## Validation

- `cd backend && python3 manage.py test api -v2 --noinput`
- `cd frontend && npm run build`
