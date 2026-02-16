# API Module Layout

`api` is organized by responsibility so new code has a clear home.

## Entry points

- `urls.py`: route definitions.
- `views.py`: stable export surface used by `urls.py` and any legacy imports.

## Tools

`tools/` is the canonical home for infrastructure and integration utilities.

- `tools/auth/clerk.py`: Clerk JWT verification plus Clerk Backend SDK client helpers.
- `tools/auth/authentication.py`: DRF authentication class (`ClerkJWTAuthentication`).
- `tools/email/resend.py`: transactional email senders and Resend integration.
- `tools/database/supabase.py`: Supabase client and configuration helpers.
- `tools/storage/block_storage.py`: signed download URL generation (Supabase or S3).

## View modules

- `views_modules/helpers.py`: shared request context, claim parsing, profile/account sync, and utility helpers.
- `views_modules/common.py`: public and general authenticated views (`/health`, `/me`, `/projects`, `/products`, `/supabase/profile`, `/me/clerk`, AI helpers).
- `views_modules/account.py`: account, checkout, order confirmation, downloads, bookings, and payment fulfillment helpers.
- `views_modules/seller.py`: seller catalog management for products, prices, assets, and service offers.

## Serializers

`serializers/` is split by domain:

- `serializers/common.py`: profile and project serializers.
- `serializers/catalog.py`: public and seller catalog serializers.
- `serializers/commerce.py`: account, order, subscription, entitlement, download, and booking serializers.
- `serializers/__init__.py`: export surface consumed by views.

## Domain modules

- `models.py`: Django data models.
- `webhooks.py`: Clerk webhook verification and event handlers.
- `billing.py`: billing feature extraction and tier inference helpers.
- `tests.py`: API and integration tests.

## Compatibility shims

These files remain as import-stable shims and forward to canonical modules:

- `authentication.py`
- `clerk.py`
- `clerk_client.py`
- `emails.py`
- `supabase_client.py`
- `block_storage.py`

## Rule for future changes

When adding a view or utility:

1. Put implementation in the appropriate canonical package (`views_modules/`, `tools/`, `serializers/`).
2. Re-export from the relevant facade (`views.py` or `serializers/__init__.py`) when needed.
3. Add route wiring in `urls.py` for new endpoints.
4. Add or update tests in `tests.py`.
