# 02 First Revenue Loop

Goal: publish one offer and complete one end-to-end purchase flow.

This is the fastest path to prove your stack can make money.

## 1. Seed a published digital product and one-time price

Run this from backend:

```bash
cd ./backend
source .venv/bin/activate
python3 manage.py shell <<'PY'
from api.models import Price, Product, Profile

owner, _ = Profile.objects.get_or_create(
    clerk_user_id="seller_demo_owner",
    defaults={"email": "seller@example.com", "first_name": "Demo", "last_name": "Seller"},
)

product, _ = Product.objects.get_or_create(
    owner=owner,
    slug="focus-sprint-kit",
    defaults={
        "name": "Focus Sprint Kit",
        "tagline": "Plan your week in 20 minutes.",
        "description": "Templates and checklists for weekly planning and execution.",
        "product_type": Product.ProductType.DIGITAL,
        "visibility": Product.Visibility.PUBLISHED,
        "feature_keys": ["focus_sprint"],
    },
)

price, _ = Price.objects.get_or_create(
    product=product,
    name="Starter",
    defaults={
        "amount_cents": 2900,
        "currency": "USD",
        "billing_period": Price.BillingPeriod.ONE_TIME,
        "is_active": True,
        "is_default": True,
        "metadata": {},
    },
)

if not price.is_default:
    price.is_default = True
    price.save(update_fields=["is_default", "updated_at"])

if product.active_price_id != price.id:
    product.active_price = price
    product.save(update_fields=["active_price", "updated_at"])

print({"product_id": product.id, "price_id": price.id, "slug": product.slug})
PY
```

Verify the catalog:

```bash
curl http://127.0.0.1:8000/api/products/
```

You should see `focus-sprint-kit` in the response.

## 2. Enable local manual checkout simulation

This is for local development only.

Set in `backend/.env`:

```bash
ORDER_CONFIRM_ALLOW_MANUAL=True
```

Set in `frontend/.env`:

```bash
VITE_ENABLE_DEV_MANUAL_CHECKOUT=true
```

Restart backend and frontend.

## 3. Complete one digital purchase in UI

1. Open `http://127.0.0.1:5173/products`
2. Sign in with Clerk
3. Open the seeded product
4. Click `Buy Now`
5. You should land on `/checkout/success`

What just happened:

- Frontend called `POST /api/account/orders/create/`
- Frontend called `POST /api/account/orders/<public_id>/confirm/` with `provider=manual`
- Backend marked order paid, fulfilled it, and created entitlements

## 4. Verify purchase data in DB

```bash
cd ./backend
source .venv/bin/activate
python3 manage.py shell <<'PY'
from api.models import Entitlement, Order

latest = Order.objects.order_by("-created_at").prefetch_related("items").first()
if not latest:
    print("No orders found")
else:
    print({
        "order": str(latest.public_id),
        "status": latest.status,
        "total_cents": latest.total_cents,
        "items": latest.items.count(),
    })

entitlements = Entitlement.objects.order_by("-created_at")[:5]
print("recent_entitlements", [e.feature_key for e in entitlements])
PY
```

If Resend is configured, this fulfillment should also trigger a transactional order confirmation email.

## 5. Seed a recurring AI subscription offer

Run this from backend:

```bash
cd ./backend
source .venv/bin/activate
python3 manage.py shell <<'PY'
from api.models import Price, Product, Profile

owner, _ = Profile.objects.get_or_create(
    clerk_user_id="seller_demo_owner",
    defaults={"email": "seller@example.com", "first_name": "Demo", "last_name": "Seller"},
)

product, _ = Product.objects.get_or_create(
    owner=owner,
    slug="agent-chat-pro",
    defaults={
        "name": "Agent Chat Pro",
        "tagline": "Ship AI support with monthly usage limits.",
        "description": "Subscription starter for token, image, and video usage products.",
        "product_type": Product.ProductType.DIGITAL,
        "visibility": Product.Visibility.PUBLISHED,
        "feature_keys": ["ai_chat", "ai_images", "ai_video"],
    },
)

price, _ = Price.objects.get_or_create(
    product=product,
    name="Pro Monthly",
    defaults={
        "amount_cents": 2900,
        "currency": "USD",
        "billing_period": Price.BillingPeriod.MONTHLY,
        "is_active": True,
        "is_default": True,
        "metadata": {},
    },
)

if product.active_price_id != price.id:
    product.active_price = price
    product.save(update_fields=["active_price", "updated_at"])

print({"product_id": product.id, "price_id": price.id, "slug": product.slug})
PY
```

## 6. Validate subscription and usage surfaces

1. Go to `/products` and buy `Agent Chat Pro`
2. Open `/account/subscriptions` and confirm record appears
3. Open `/app` and check AI provider and usage cards
4. Hit API directly:

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/api/ai/providers/
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/api/ai/usage/summary/
```

These usage values are placeholders until you wire provider telemetry.

## 7. Verify booking confirmation email flow

Create a booking request from frontend (`/account/bookings`) or API:

```bash
curl -X POST http://127.0.0.1:8000/api/account/bookings/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "service_offer": PUT_SERVICE_OFFER_ID_HERE,
    "customer_notes": "Need onboarding help."
  }'
```

If Resend is configured, booking creation should trigger a transactional booking confirmation email.

## 8. Production safety reset

Before real deployment, set these back:

```bash
# backend/.env
ORDER_CONFIRM_ALLOW_MANUAL=False
ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=False

# frontend/.env
VITE_ENABLE_DEV_MANUAL_CHECKOUT=false
```

Production should rely on verified Clerk webhooks for payment confirmation.
