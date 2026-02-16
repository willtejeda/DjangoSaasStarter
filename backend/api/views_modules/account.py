from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as django_timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..tools.storage.block_storage import (
    BlockStorageConfigurationError,
    BlockStorageError,
    build_digital_asset_download_url,
)
from ..tools.email.resend import (
    resend_is_configured,
    send_booking_requested_email,
    send_order_fulfilled_email,
    send_preflight_test_email,
)
from ..models import (
    Booking,
    DownloadGrant,
    Entitlement,
    Order,
    OrderItem,
    PaymentTransaction,
    Price,
    Product,
    ServiceOffer,
    Subscription,
)
from ..serializers import (
    BookingSerializer,
    CustomerAccountSerializer,
    DownloadGrantSerializer,
    EntitlementSerializer,
    OrderConfirmSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    SubscriptionSerializer,
)
from .helpers import _safe_dict, _safe_str, get_request_customer_account

logger = logging.getLogger(__name__)


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

    # Best-effort transactional email. Purchase flow should not fail if email delivery fails.
    send_order_fulfilled_email(order)
    return order


def _order_confirm_secret_valid(request) -> bool:
    expected_secret = str(getattr(settings, "ORDER_CONFIRM_SHARED_SECRET", "") or "").strip()
    if not expected_secret:
        return True

    provided_secret = str(request.headers.get("X-Order-Confirm-Secret", "") or "").strip()
    return bool(provided_secret) and secrets.compare_digest(provided_secret, expected_secret)


def confirm_order_payment(
    order: Order,
    *,
    provider: str,
    external_id: str = "",
    clerk_checkout_id: str = "",
    raw_payload: dict[str, Any] | None = None,
) -> tuple[Order, bool]:
    if order.status in {Order.Status.CANCELED, Order.Status.REFUNDED}:
        raise ValidationError("Cannot confirm a canceled or refunded order.")

    if order.status in {Order.Status.PAID, Order.Status.FULFILLED}:
        if order.status == Order.Status.PAID:
            order = _fulfill_order(order)
        return order, True

    raw_payload = raw_payload if isinstance(raw_payload, dict) else {}
    external_id = _safe_str(external_id)
    clerk_checkout_id = _safe_str(clerk_checkout_id)

    now = django_timezone.now()
    order.status = Order.Status.PAID
    order.paid_at = order.paid_at or now
    if clerk_checkout_id and not order.clerk_checkout_id:
        order.clerk_checkout_id = clerk_checkout_id
    if external_id and not order.external_reference:
        order.external_reference = external_id
    order.save(
        update_fields=[
            "status",
            "paid_at",
            "clerk_checkout_id",
            "external_reference",
            "updated_at",
        ]
    )

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
        if item.price and item.price.billing_period in {Price.BillingPeriod.MONTHLY, Price.BillingPeriod.YEARLY}
    ]

    for index, item in enumerate(recurring_items):
        existing_subscription = Subscription.objects.filter(
            customer_account=order.customer_account,
            price=item.price,
            metadata__order_public_id=str(order.public_id),
            metadata__order_item_id=item.id,
        ).exists()
        if existing_subscription:
            continue

        period_start = now
        period_end = _billing_period_end(period_start, item.price.billing_period)

        subscription_id = None
        if provider == PaymentTransaction.Provider.CLERK and external_id and index == 0:
            if not Subscription.objects.filter(clerk_subscription_id=external_id).exists():
                subscription_id = external_id

        Subscription.objects.create(
            customer_account=order.customer_account,
            product=item.product,
            price=item.price,
            status=Subscription.Status.ACTIVE,
            clerk_subscription_id=subscription_id,
            current_period_start=period_start,
            current_period_end=period_end,
            metadata={
                "order_public_id": str(order.public_id),
                "order_item_id": item.id,
                "quantity": item.quantity,
            },
        )

    order = _fulfill_order(order)
    return order, False


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


class AccountPreflightEmailTestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not resend_is_configured():
            logger.warning("Preflight email test requested without Resend configuration.")
            return Response(
                {
                    "sent": False,
                    "detail": (
                        "Resend is not configured. Set RESEND_API_KEY and RESEND_FROM_EMAIL in backend/.env."
                    ),
                },
                status=400,
            )

        account = get_request_customer_account(request)
        sent, recipient = send_preflight_test_email(account)
        if not sent:
            logger.warning("Preflight email send failed for account %s.", account.id)
            return Response(
                {
                    "sent": False,
                    "detail": (
                        "Preflight email failed. Check sender verification, recipient email, and backend logs."
                    ),
                },
                status=502,
            )

        sent_at = django_timezone.now()
        metadata = account.metadata if isinstance(account.metadata, dict) else {}
        metadata["preflight_email_last_sent_at"] = sent_at.isoformat()
        metadata["preflight_email_last_recipient"] = recipient
        account.metadata = metadata
        account.save(update_fields=["metadata", "updated_at"])
        logger.info("Preflight email send succeeded for account %s to %s.", account.id, recipient)

        return Response(
            {
                "sent": True,
                "detail": f"Preflight email sent to {recipient}.",
                "recipient_email": recipient,
                "sent_at": sent_at.isoformat(),
            }
        )


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
    throttle_scope = "checkout_create"

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
        logger.info(
            "Created pending order %s for account %s (price_id=%s, quantity=%s).",
            order.public_id,
            account.id,
            price.id,
            quantity,
        )

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
    throttle_scope = "order_confirm"

    @transaction.atomic
    def post(self, request, public_id):
        account = get_request_customer_account(request)
        order = get_object_or_404(
            Order.objects.select_for_update()
            .select_related("customer_account")
            .prefetch_related("items__product", "items__price"),
            public_id=public_id,
            customer_account=account,
        )

        serializer = OrderConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        external_id = _safe_str(serializer.validated_data.get("external_id"))
        clerk_checkout_id = _safe_str(serializer.validated_data.get("clerk_checkout_id"))
        raw_payload = _safe_dict(serializer.validated_data.get("raw_payload"))

        if order.status == Order.Status.PENDING_PAYMENT:
            if provider == PaymentTransaction.Provider.MANUAL and not settings.ORDER_CONFIRM_ALLOW_MANUAL:
                return Response(
                    {
                        "detail": (
                            "Manual order confirmation is disabled. "
                            "Set ORDER_CONFIRM_ALLOW_MANUAL=True for controlled development use."
                        )
                    },
                    status=403,
                )
            if (
                provider == PaymentTransaction.Provider.CLERK
                and not settings.ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM
            ):
                return Response(
                    {
                        "detail": (
                            "Direct client-side Clerk confirmation is disabled. "
                            "Wait for a verified payment webhook to mark this order paid."
                        ),
                        "pending_verification": True,
                    },
                    status=409,
                )
            if not _order_confirm_secret_valid(request):
                return Response(
                    {
                        "detail": (
                            "Invalid order confirmation secret. "
                            "Pass X-Order-Confirm-Secret with a valid server-side value."
                        )
                    },
                    status=403,
                )

        order, already_confirmed = confirm_order_payment(
            order,
            provider=provider,
            external_id=external_id,
            clerk_checkout_id=clerk_checkout_id,
            raw_payload=raw_payload,
        )
        logger.info(
            "Order confirmation requested for %s by account %s via %s (already_confirmed=%s).",
            order.public_id,
            account.id,
            provider,
            already_confirmed,
        )
        return Response({"order": OrderSerializer(order).data, "already_confirmed": already_confirmed})


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
    throttle_scope = "download_access"

    def post(self, request, token):
        account = get_request_customer_account(request)
        grant = get_object_or_404(
            DownloadGrant.objects.select_related("asset", "asset__product"),
            token=token,
            customer_account=account,
        )

        if not grant.can_download:
            logger.warning("Blocked download attempt for inactive grant %s (account=%s).", grant.token, account.id)
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
        logger.info("Created download link for grant %s (account=%s).", grant.token, account.id)

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
        # Best-effort transactional email. Booking creation remains source-of-truth.
        send_booking_requested_email(booking)
        logger.info(
            "Created booking %s for account %s (service_offer=%s, order_item=%s).",
            booking.id,
            account.id,
            service_offer.id,
            order_item.id if order_item else None,
        )
        return Response(BookingSerializer(booking).data, status=201)
