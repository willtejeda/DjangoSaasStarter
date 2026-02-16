# API Module Layout

`api` is organized by responsibility so new code has a clear home.

## Entry points

- `urls.py`: route definitions.
- `views.py`: stable export surface used by `urls.py` and any legacy imports.

## View modules

- `views_modules/helpers.py`: shared request context, claim parsing, profile/account sync, and utility helpers.
- `views_modules/common.py`: public and general authenticated views (`/health`, `/me`, `/projects`, `/products`, `/supabase/profile`, `/me/clerk`, AI helpers).
- `views_modules/account.py`: account, checkout, order confirmation, downloads, bookings, and payment fulfillment helpers.
- `views_modules/seller.py`: seller catalog management for products, prices, assets, and service offers.

## Integration and domain modules

- `webhooks.py`: Clerk webhook verification and event handlers.
- `emails.py`: transactional email providers and templates.
- `block_storage.py`: signed URL generation and storage backend integration.
- `billing.py`: billing feature extraction and tier inference helpers.

## Data and API contracts

- `models.py`: Django data models.
- `serializers.py`: DRF serializers.
- `tests.py`: API and integration tests.

## Rule for future changes

When adding a view:

1. Put implementation in the appropriate file under `views_modules/`.
2. Re-export it from `views.py`.
3. Add route wiring in `urls.py`.
4. Add or update tests in `tests.py`.
