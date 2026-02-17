# 08 Security Pass (Phase 1)

Date: February 16, 2026

## Scope

- Frontend exposure review
- Backend response hardening
- Starter-safe defaults for production

## Frontend findings

### 1. No API secrets embedded in shipped frontend code

Current frontend uses only public config keys:

- `VITE_CLERK_PUBLISHABLE_KEY`
- `VITE_API_BASE_URL`
- `VITE_CLERK_BILLING_PORTAL_URL`

No secret keys are read in browser code.

### 2. Backend 5xx detail was previously surfaced directly

Change made:

- `./frontend/src/lib/api.ts` now masks raw 5xx details by default.
- Optional local override added: `VITE_EXPOSE_BACKEND_ERRORS=true`.

Impact:

- Better protection against accidental internal error leakage in production UI.

### 3. Added user feedback for async actions

Change made:

- Added toast system in `./frontend/src/components/feedback/toast.tsx`.

Impact:

- Users can see action outcomes without opening console logs.
- Better UX for preflight and account operations.

## Backend findings and changes

### 1. Clerk user endpoint returned `private_metadata`

Risk:

- Could leak sensitive internal metadata to clients.

Change made:

- Removed `private_metadata` from `/api/me/clerk/` response in `./backend/api/views_modules/common.py`.

### 2. Supabase and Clerk error internals could leak in production

Change made:

- Error payload now includes exception details only when `DJANGO_DEBUG=True`.
- Production responses return safe high-level detail messages.

### 3. Added verbose operational logging defaults

Change made:

- Added logging config in `./backend/project_settings/settings.py`.
- Added `DJANGO_LOG_LEVEL` and `API_LOG_LEVEL` in `./backend/.env.example`.
- Added structured logs for order creation, order confirmation, preflight email sends, download link generation, and work order creation.

Impact:

- Better observability for AI-assisted development and support workflows.

## Existing strong defaults already present

- HTTPS and secure cookie defaults when `DJANGO_DEBUG=False`
- DRF throttling enabled
- Webhook-first payment flow contract
- Manual/client-side payment confirmation disabled by default

## Recommended Phase 2 hardening

1. Add `django-csp` with strict policy and nonces where needed.
2. Add Sentry (or equivalent) for production exception monitoring.
3. Add audit logs for sensitive account changes.
4. Add explicit permission tests around seller endpoints for multi-tenant scenarios.
