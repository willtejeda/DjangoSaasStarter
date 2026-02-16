---
name: frontend-backend-contract
description: Use when frontend types or API payload handling changes to keep contracts synced.
---

# Frontend Backend Contract

## Workflow

1. Inspect API payload shape in backend serializers and views.
2. Inspect frontend usage in:
   - `frontend/src/features/app-shell/types.ts`
   - `frontend/src/lib/api.ts`
   - `frontend/src/app.tsx`
3. Update types and request handlers to match backend payloads.
4. Add or update tests for affected backend endpoints.

## Output contract

Return:

- contract deltas
- frontend types updated
- backend endpoints validated
- regressions prevented

## Validation

- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `cd backend && python3 manage.py test api -v2 --noinput`
