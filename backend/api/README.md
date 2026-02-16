# API Module Layout

`api/` is split by responsibility so contributors and agents can change one area without scanning a monolith.

## Top-level map

- `urls.py`: route declarations.
- `views.py`: stable export facade used by `urls.py`.
- `admin.py`: Django admin registrations.
- `middleware.py`: optional request middleware.

## `models/` package

Django model classes are grouped by domain:

- `models/accounts.py`
  - `Profile`
  - `Project`
  - `CustomerAccount`
- `models/catalog.py`
  - `Product`
  - `Price`
  - `DigitalAsset`
  - `ServiceOffer`
- `models/commerce.py`
  - `Order`
  - `OrderItem`
  - `Subscription`
  - `PaymentTransaction`
  - `WebhookEvent`
  - `Entitlement`
  - `DownloadGrant`
  - `Booking`
- `models/__init__.py`: canonical export surface (`from api.models import ...`).

## `serializers/` package

- `serializers/common.py`: profile and project serializers.
- `serializers/catalog.py`: public and seller catalog serializers.
- `serializers/commerce.py`: account, order, subscription, entitlement, download, and booking serializers.
- `serializers/__init__.py`: canonical serializer exports.

## `views_modules/` package

- `views_modules/helpers.py`: shared request context helpers and AI usage payload helpers.
- `views_modules/common.py`: health, profile, project, public product, AI, and Supabase probe endpoints.
- `views_modules/account.py`: buyer account endpoints and order fulfillment flow.
- `views_modules/seller.py`: seller catalog and pricing management endpoints.

## `tools/` package

External integration and platform utility code lives here:

- `tools/auth/`: Clerk JWT verification and DRF auth.
- `tools/billing/`: billing claim parsing and plan tier inference.
- `tools/database/`: Supabase client configuration.
- `tools/email/`: Resend transactional email helpers.
- `tools/storage/`: signed download URL generation for Supabase and S3-compatible storage.

## `webhooks/` package

Clerk webhook processing is split for clarity:

- `webhooks/verification.py`: Svix signature verification.
- `webhooks/helpers.py`: payload parsing and lookup utilities.
- `webhooks/handlers.py`: webhook event handlers and event map.
- `webhooks/receiver.py`: Django view that verifies, deduplicates, and dispatches events.
- `webhooks/__init__.py`: canonical exports (`from api.webhooks import ...`).

## `tests/` package

Tests are grouped by concern:

- `tests/test_auth.py`: auth, billing-claim parsing, and Supabase URL helper tests.
- `tests/test_webhooks.py`: webhook verification, event mapping, and user sync handlers.
- `tests/test_project_api.py`: me/projects/ai/preflight tests.
- `tests/test_commerce_api.py`: checkout, fulfillment, downloads, booking, and security flags.

## Change rules

1. Keep domain logic in the domain package (`models/`, `webhooks/`, `views_modules/`, `tools/`).
2. Keep `views.py`, `serializers/__init__.py`, and `models/__init__.py` as import-stable facades.
3. Add or update tests in `tests/` with the same domain split.
4. Run backend tests and deploy checks after structural edits.
