from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as django_timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .block_storage import (
    BlockStorageConfigurationError,
    BlockStorageError,
    build_digital_asset_download_url,
)
from .billing import (
    extract_billing_features as extract_billing_features_from_claims,
    infer_plan_tier as infer_plan_tier_from_features,
)
from .models import (
    Booking,
    CustomerAccount,
    DigitalAsset,
    DownloadGrant,
    Entitlement,
    Order,
    OrderItem,
    PaymentTransaction,
    Price,
    Product,
    Profile,
    Project,
    ServiceOffer,
    Subscription,
)
from .serializers import (
    BookingSerializer,
    CustomerAccountSerializer,
    DownloadGrantSerializer,
    EntitlementSerializer,
    OrderConfirmSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProfileSerializer,
    ProjectSerializer,
    SellerAssetSerializer,
    SellerPriceSerializer,
    SellerProductSerializer,
    ServiceOfferSerializer,
    ServiceOfferUpsertSerializer,
    SubscriptionSerializer,
)
from .supabase_client import SupabaseConfigurationError, get_supabase_client


def extract_billing_features(claims: dict[str, Any]) -> list[str]:
    """Backward-compatible local wrapper used by existing tests."""
    return extract_billing_features_from_claims(claims)


def infer_plan_tier(features: list[str]) -> str:
    """Backward-compatible local wrapper used by existing code paths."""
    return infer_plan_tier_from_features(features)


def _safe_str(value: Any) -> str:
    return str(value).strip() if value else ""


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def sync_profile_from_claims(claims: dict[str, Any]) -> Profile | None:
    clerk_user_id = _safe_str(claims.get("sub"))
    if not clerk_user_id:
        return None

    billing_features = extract_billing_features(claims)
    metadata = claims.get("metadata") if isinstance(claims.get("metadata"), dict) else {}
    defaults = {
        "email": _safe_str(claims.get("email")),
        "first_name": _safe_str(claims.get("given_name") or claims.get("first_name")),
        "last_name": _safe_str(claims.get("family_name") or claims.get("last_name")),
        "image_url": _safe_str(claims.get("picture") or claims.get("image_url")),
        "plan_tier": infer_plan_tier(billing_features),
        "billing_features": billing_features,
        "is_active": True,
        "metadata": metadata,
    }
    profile, created = Profile.objects.get_or_create(
        clerk_user_id=clerk_user_id,
        defaults=defaults,
    )

    if not created:
        changed_fields: list[str] = []
        for field_name, field_value in defaults.items():
            if getattr(profile, field_name) != field_value:
                setattr(profile, field_name, field_value)
                changed_fields.append(field_name)
        if changed_fields:
            profile.save(update_fields=[*changed_fields, "updated_at"])

    return profile


def get_request_claims(request) -> dict[str, Any]:
    claims = getattr(request, "clerk_claims", request.auth or {})
    return claims if isinstance(claims, dict) else {}


def get_request_profile(request) -> Profile:
    cached_profile = getattr(request, "_cached_profile", None)
    if cached_profile is not None:
        return cached_profile

    profile = sync_profile_from_claims(get_request_claims(request))
    if profile is None:
        raise ValidationError("Missing Clerk identity in token claims.")

    request._cached_profile = profile
    return profile


def get_request_customer_account(request) -> CustomerAccount:
    cached_account = getattr(request, "_cached_customer_account", None)
    if cached_account is not None:
        return cached_account

    profile = get_request_profile(request)
    defaults = {
        "external_customer_id": profile.clerk_user_id,
        "billing_email": profile.email,
        "full_name": profile.display_name,
    }
    account, created = CustomerAccount.objects.get_or_create(profile=profile, defaults=defaults)

    if not created:
        changed_fields: list[str] = []
        if not account.billing_email and profile.email:
            account.billing_email = profile.email
            changed_fields.append("billing_email")
        if not account.full_name and profile.display_name:
            account.full_name = profile.display_name
            changed_fields.append("full_name")
        if not account.external_customer_id and profile.clerk_user_id:
            account.external_customer_id = profile.clerk_user_id
            changed_fields.append("external_customer_id")
        if changed_fields:
            account.save(update_fields=[*changed_fields, "updated_at"])

    request._cached_customer_account = account
    return account


def _billing_period_end(start_at, billing_period: str):
    if billing_period == Price.BillingPeriod.MONTHLY:
        return start_at + timedelta(days=30)
    if billing_period == Price.BillingPeriod.YEARLY:
        return start_at + timedelta(days=365)
    return None


def _fulfill_order(order: Order) -> Order:
    if order.status == Order.Status.FULFILLED:
        return order

    now = django_timezone.now()
    items = list(
        order.items.select_related("product", "price")
        .prefetch_related("product__assets")
        .order_by("id")
    )

    for item in items:
        product = item.product
        feature_keys = product.feature_keys if isinstance(product.feature_keys, list) else []

        for feature_key in feature_keys:
            Entitlement.objects.get_or_create(
                customer_account=order.customer_account,
                feature_key=str(feature_key).strip().lower(),
                source_type=Entitlement.SourceType.PURCHASE,
                source_reference=str(order.public_id),
                defaults={
                    "starts_at": now,
                    "is_active": True,
                    "metadata": {"order_item_id": item.id},
                },
            )

        if product.product_type == Product.ProductType.DIGITAL:
            for asset in product.assets.filter(is_active=True):
                DownloadGrant.objects.get_or_create(
                    customer_account=order.customer_account,
                    order_item=item,
                    asset=asset,
                    defaults={"max_downloads": 5, "is_active": True},
                )

        if product.product_type == Product.ProductType.SERVICE and hasattr(product, "service_offer"):
            existing_count = Booking.objects.filter(order_item=item).count()
            needed = max((item.quantity or 1) - existing_count, 0)
            for _ in range(needed):
                Booking.objects.create(
                    customer_account=order.customer_account,
                    service_offer=product.service_offer,
                    order_item=item,
                    status=Booking.Status.REQUESTED,
                )

    order.status = Order.Status.FULFILLED
    order.fulfilled_at = order.fulfilled_at or now
    order.paid_at = order.paid_at or now
    order.save(update_fields=["status", "fulfilled_at", "paid_at", "updated_at"])
    return order


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        billing_features = extract_billing_features(claims)
        profile = sync_profile_from_claims(claims)
        customer_account = get_request_customer_account(request)

        return Response(
            {
                "clerk_user_id": claims.get("sub"),
                "email": claims.get("email"),
                "org_id": claims.get("org_id"),
                "billing_features": billing_features,
                "profile": ProfileSerializer(profile).data if profile else None,
                "customer_account": CustomerAccountSerializer(customer_account).data,
            }
        )


class BillingFeatureView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        enabled_features = set(extract_billing_features(claims))
        requested_feature = request.query_params.get("feature")

        if requested_feature:
            normalized_feature = str(requested_feature).strip().lower()
            return Response(
                {
                    "feature": normalized_feature,
                    "enabled": normalized_feature in enabled_features,
                }
            )

        return Response({"enabled_features": sorted(enabled_features)})


class SupabaseProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return Response({"detail": "Missing Clerk user id in token claims."}, status=400)

        try:
            supabase = get_supabase_client(access_token=getattr(request, "clerk_token", None))
            result = (
                supabase.table("profiles")
                .select("*")
                .eq("clerk_user_id", clerk_user_id)
                .limit(1)
                .execute()
            )
        except SupabaseConfigurationError as exc:
            return Response({"detail": str(exc)}, status=500)
        except Exception as exc:  # pragma: no cover
            return Response(
                {
                    "detail": "Supabase query failed. Confirm table and RLS setup.",
                    "error": str(exc),
                },
                status=502,
            )

        data = getattr(result, "data", None)
        profile = data[0] if isinstance(data, list) and data else data
        return Response({"profile": profile})


class ClerkUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = get_request_claims(request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return Response(
                {"detail": "Missing Clerk user id in token claims."}, status=400
            )

        try:
            from .clerk_client import ClerkClientError, get_clerk_user

            user = get_clerk_user(clerk_user_id)
        except ClerkClientError as exc:
            return Response({"detail": str(exc)}, status=500)
        except Exception as exc:
            return Response(
                {"detail": "Clerk API call failed.", "error": str(exc)},
                status=502,
            )

        email_addresses = []
        if hasattr(user, "email_addresses") and user.email_addresses:
            email_addresses = [
                {
                    "email": ea.email_address,
                    "verified": getattr(getattr(ea, "verification", None), "status", None) == "verified",
                }
                for ea in user.email_addresses
            ]

        return Response(
            {
                "clerk_user_id": user.id,
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "image_url": getattr(user, "image_url", None),
                "email_addresses": email_addresses,
                "public_metadata": getattr(user, "public_metadata", {}),
                "private_metadata": getattr(user, "private_metadata", {}),
                "created_at": getattr(user, "created_at", None),
                "last_sign_in_at": getattr(user, "last_sign_in_at", None),
            }
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_request_profile(request)
        return Response(ProfileSerializer(profile).data)


class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Project.objects.filter(owner=profile)

    def perform_create(self, serializer):
        profile = get_request_profile(self.request)
        serializer.save(owner=profile)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Project.objects.filter(owner=profile)


class PublicProductListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        return (
            Product.objects.filter(visibility=Product.Visibility.PUBLISHED)
            .select_related("active_price")
            .prefetch_related("prices", "assets")
            .order_by("name")
        )


class PublicProductDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(visibility=Product.Visibility.PUBLISHED)
            .select_related("active_price", "service_offer")
            .prefetch_related("prices", "assets")
        )


class AccountCustomerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = get_request_customer_account(request)
        return Response(CustomerAccountSerializer(account).data)

    def patch(self, request):
        account = get_request_customer_account(request)
        serializer = CustomerAccountSerializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AccountOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return (
            Order.objects.filter(customer_account=account)
            .prefetch_related("items__product", "items__price")
            .order_by("-created_at")
        )


class AccountOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        price = get_object_or_404(
            Price.objects.select_related("product"),
            pk=serializer.validated_data["price_id"],
            is_active=True,
            product__visibility=Product.Visibility.PUBLISHED,
        )
        quantity = serializer.validated_data["quantity"]
        notes = _safe_str(serializer.validated_data.get("notes"))

        subtotal_cents = price.amount_cents * quantity
        account = get_request_customer_account(request)

        order = Order.objects.create(
            customer_account=account,
            status=Order.Status.PENDING_PAYMENT,
            currency=price.currency,
            subtotal_cents=subtotal_cents,
            tax_cents=0,
            total_cents=subtotal_cents,
            notes=notes,
        )
        OrderItem.objects.create(
            order=order,
            product=price.product,
            price=price,
            quantity=quantity,
            unit_amount_cents=price.amount_cents,
            product_name_snapshot=price.product.name,
            price_name_snapshot=price.name or price.get_billing_period_display(),
        )

        checkout_url = ""
        metadata = price.metadata if isinstance(price.metadata, dict) else {}
        checkout_url = _safe_str(metadata.get("checkout_url"))

        return Response(
            {
                "order": OrderSerializer(order).data,
                "checkout": {
                    "checkout_url": checkout_url,
                    "provider": "clerk",
                },
            },
            status=201,
        )


class AccountOrderConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, public_id):
        account = get_request_customer_account(request)
        order = get_object_or_404(
            Order.objects.select_related("customer_account").prefetch_related("items__product", "items__price"),
            public_id=public_id,
            customer_account=account,
        )

        serializer = OrderConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if order.status in {Order.Status.CANCELED, Order.Status.REFUNDED}:
            return Response({"detail": "Cannot confirm a canceled or refunded order."}, status=400)

        if order.status in {Order.Status.PAID, Order.Status.FULFILLED}:
            if order.status == Order.Status.PAID:
                order = _fulfill_order(order)
            return Response({"order": OrderSerializer(order).data, "already_confirmed": True})

        provider = serializer.validated_data["provider"]
        external_id = _safe_str(serializer.validated_data.get("external_id"))
        clerk_checkout_id = _safe_str(serializer.validated_data.get("clerk_checkout_id"))
        raw_payload = _safe_dict(serializer.validated_data.get("raw_payload"))

        now = django_timezone.now()
        order.status = Order.Status.PAID
        order.paid_at = now
        if clerk_checkout_id:
            order.clerk_checkout_id = clerk_checkout_id
        if external_id:
            order.external_reference = external_id
        order.save(update_fields=["status", "paid_at", "clerk_checkout_id", "external_reference", "updated_at"])

        if external_id:
            PaymentTransaction.objects.update_or_create(
                provider=provider,
                external_id=external_id,
                order=order,
                defaults={
                    "subscription": None,
                    "status": PaymentTransaction.Status.SUCCEEDED,
                    "amount_cents": order.total_cents,
                    "currency": order.currency,
                    "raw_payload": raw_payload,
                },
            )
        else:
            PaymentTransaction.objects.create(
                order=order,
                provider=provider,
                status=PaymentTransaction.Status.SUCCEEDED,
                amount_cents=order.total_cents,
                currency=order.currency,
                raw_payload=raw_payload,
            )

        recurring_items = [
            item
            for item in order.items.select_related("product", "price")
            if item.price
            and item.price.billing_period in {Price.BillingPeriod.MONTHLY, Price.BillingPeriod.YEARLY}
        ]

        for index, item in enumerate(recurring_items):
            period_start = now
            period_end = _billing_period_end(period_start, item.price.billing_period)

            subscription_id = None
            if provider == PaymentTransaction.Provider.CLERK and external_id and index == 0:
                if not Subscription.objects.filter(clerk_subscription_id=external_id).exists():
                    subscription_id = external_id

            Subscription.objects.create(
                customer_account=account,
                product=item.product,
                price=item.price,
                status=Subscription.Status.ACTIVE,
                clerk_subscription_id=subscription_id,
                current_period_start=period_start,
                current_period_end=period_end,
                metadata={"order_public_id": str(order.public_id), "quantity": item.quantity},
            )

        order = _fulfill_order(order)
        return Response({"order": OrderSerializer(order).data, "already_confirmed": False})


class AccountSubscriptionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return Subscription.objects.filter(customer_account=account).select_related("product", "price")


class AccountEntitlementListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EntitlementSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        queryset = Entitlement.objects.filter(customer_account=account).order_by("feature_key")
        current_only = str(self.request.query_params.get("current", "true")).lower() in {"1", "true", "yes"}
        if current_only:
            now = django_timezone.now()
            queryset = queryset.filter(
                is_active=True,
                starts_at__lte=now,
            ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        return queryset


class AccountDownloadGrantListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DownloadGrantSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return (
            DownloadGrant.objects.filter(customer_account=account)
            .select_related("asset", "asset__product", "order_item")
            .order_by("-created_at")
        )


class AccountDownloadAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        account = get_request_customer_account(request)
        grant = get_object_or_404(
            DownloadGrant.objects.select_related("asset", "asset__product"),
            token=token,
            customer_account=account,
        )

        if not grant.can_download:
            return Response(
                {
                    "detail": "Download grant is inactive, expired, or out of attempts.",
                    "grant": DownloadGrantSerializer(grant).data,
                },
                status=403,
            )

        try:
            download_url = build_digital_asset_download_url(grant.asset.file_path)
        except BlockStorageConfigurationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except BlockStorageError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        now = django_timezone.now()
        grant.download_count += 1
        grant.last_downloaded_at = now
        grant.save(update_fields=["download_count", "last_downloaded_at", "updated_at"])

        return Response(
            {
                "download_url": download_url,
                "grant": DownloadGrantSerializer(grant).data,
            }
        )


class AccountBookingListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return (
            Booking.objects.filter(customer_account=account)
            .select_related("service_offer", "service_offer__product", "order_item")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        account = get_request_customer_account(request)
        service_offer_id = request.data.get("service_offer")
        order_item_id = request.data.get("order_item")
        customer_notes = _safe_str(request.data.get("customer_notes"))

        if not service_offer_id:
            raise ValidationError({"service_offer": "service_offer is required."})

        service_offer = get_object_or_404(
            ServiceOffer.objects.select_related("product"),
            pk=service_offer_id,
            product__visibility=Product.Visibility.PUBLISHED,
        )

        order_item = None
        if order_item_id:
            order_item = get_object_or_404(
                OrderItem.objects.select_related("order", "product"),
                pk=order_item_id,
                order__customer_account=account,
            )
            if order_item.product_id != service_offer.product_id:
                raise ValidationError({"order_item": "Order item must match selected service offer."})

        booking = Booking.objects.create(
            customer_account=account,
            service_offer=service_offer,
            order_item=order_item,
            status=Booking.Status.REQUESTED,
            customer_notes=customer_notes,
        )
        return Response(BookingSerializer(booking).data, status=201)


class SellerProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Product.objects.filter(owner=profile).select_related("active_price", "service_offer")

    def perform_create(self, serializer):
        profile = get_request_profile(self.request)
        serializer.save(owner=profile)


class SellerProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Product.objects.filter(owner=profile).select_related("active_price", "service_offer")


class SellerPriceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerPriceSerializer

    def _get_product(self):
        profile = get_request_profile(self.request)
        return get_object_or_404(Product, pk=self.kwargs["product_id"], owner=profile)

    def get_queryset(self):
        return Price.objects.filter(product=self._get_product()).order_by("amount_cents", "id")

    def perform_create(self, serializer):
        product = self._get_product()
        price = serializer.save(product=product)

        if price.is_default:
            Price.objects.filter(product=product).exclude(pk=price.pk).update(is_default=False)
            product.active_price = price
            product.save(update_fields=["active_price", "updated_at"])
        elif product.active_price_id is None:
            product.active_price = price
            product.save(update_fields=["active_price", "updated_at"])


class SellerPriceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerPriceSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Price.objects.filter(product__owner=profile).select_related("product")

    def perform_update(self, serializer):
        price = serializer.save()
        product = price.product
        if price.is_default:
            Price.objects.filter(product=product).exclude(pk=price.pk).update(is_default=False)
            if product.active_price_id != price.id:
                product.active_price = price
                product.save(update_fields=["active_price", "updated_at"])


class SellerAssetListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerAssetSerializer

    def _get_product(self):
        profile = get_request_profile(self.request)
        return get_object_or_404(Product, pk=self.kwargs["product_id"], owner=profile)

    def get_queryset(self):
        return DigitalAsset.objects.filter(product=self._get_product()).order_by("title", "id")

    def perform_create(self, serializer):
        serializer.save(product=self._get_product())


class SellerAssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerAssetSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return DigitalAsset.objects.filter(product__owner=profile).select_related("product")


class SellerServiceOfferView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        profile = get_request_profile(request)
        product = get_object_or_404(Product, pk=product_id, owner=profile)
        if product.product_type != Product.ProductType.SERVICE:
            return Response({"detail": "Product is not a service product."}, status=400)

        if not hasattr(product, "service_offer"):
            return Response({"detail": "No service offer configured yet."}, status=404)

        return Response(ServiceOfferSerializer(product.service_offer).data)

    def put(self, request, product_id):
        return self._upsert(request, product_id)

    def patch(self, request, product_id):
        return self._upsert(request, product_id, partial=True)

    def _upsert(self, request, product_id, partial=False):
        profile = get_request_profile(request)
        product = get_object_or_404(Product, pk=product_id, owner=profile)
        if product.product_type != Product.ProductType.SERVICE:
            return Response({"detail": "Product is not a service product."}, status=400)

        service_offer = getattr(product, "service_offer", None)
        serializer = ServiceOfferUpsertSerializer(
            service_offer,
            data={**request.data, "product": product.id},
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        offer = serializer.save(product=product)
        return Response(ServiceOfferSerializer(offer).data)
