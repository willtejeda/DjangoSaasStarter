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
    send_fulfillment_order_requested_email,
    send_order_fulfilled_email,
    send_preflight_test_email,
)
from ..models import (
    DigitalAsset,
    DownloadGrant,
    Entitlement,
    FulfillmentOrder,
    Order,
    OrderItem,
    PaymentTransaction,
    Price,
    Product,
    Subscription,
    WebhookEvent,
)
from ..serializers import (
    CustomerAccountSerializer,
    DownloadGrantSerializer,
    EntitlementSerializer,
    FulfillmentOrderSerializer,
    OrderConfirmSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    SubscriptionSerializer,
)
from ..webhooks.handlers import handle_billing_subscription_canceled, handle_billing_subscription_upsert
from ..webhooks.helpers import _extract_clerk_user_id_from_subscription_payload
from .helpers import _safe_dict, _safe_str, get_request_customer_account

logger = logging.getLogger(__name__)
SUBSCRIPTION_UPSERT_EVENT_TYPES = {
    "subscription.created",
    "subscription.updated",
    "subscription.active",
    "subscription.pastDue",
    "subscription.paused",
    "billing.subscription.created",
    "billing.subscription.updated",
    "billing.subscription.active",
    "billing.subscription.pastDue",
    "billing.subscription.paused",
}
SUBSCRIPTION_CANCELED_EVENT_TYPES = {
    "subscription.canceled",
    "subscription.cancelled",
    "billing.subscription.canceled",
    "billing.subscription.cancelled",
}
SUBSCRIPTION_BACKFILL_EVENT_LIMIT = 200


def _billing_period_end(start_at, billing_period: str):
    if billing_period == Price.BillingPeriod.MONTHLY:
        return start_at + timedelta(days=30)
    if billing_period == Price.BillingPeriod.YEARLY:
        return start_at + timedelta(days=365)
    return None


def _resolve_service_delivery_mode(item: OrderItem) -> str:
    service_offer = getattr(item.product, "service_offer", None)
    metadata = service_offer.metadata if service_offer and isinstance(service_offer.metadata, dict) else {}
    raw_value = str(
        metadata.get("delivery_mode")
        or metadata.get("fulfillment_delivery_mode")
        or ""
    ).strip().lower()
    if raw_value in {"physical", "shipped", FulfillmentOrder.DeliveryMode.PHYSICAL_SHIPPED}:
        return FulfillmentOrder.DeliveryMode.PHYSICAL_SHIPPED
    return FulfillmentOrder.DeliveryMode.DOWNLOADABLE


def _create_pending_download_grant(
    order: Order,
    item: OrderItem,
    sequence: int,
    *,
    reason: str = "pending_fulfillment",
) -> DownloadGrant:
    safe_order_id = str(order.public_id)
    safe_product_name = (item.product_name_snapshot or item.product.name or "Custom deliverable").strip()
    asset = DigitalAsset.objects.create(
        product=item.product,
        title=f"{safe_product_name} deliverable #{sequence}",
        file_path=f"pending/fulfillment/{safe_order_id}/{item.id}-{sequence}.pending",
        version_label="pending",
        is_active=False,
        metadata={
            "pending_fulfillment": True,
            "pending_reason": reason,
            "order_public_id": safe_order_id,
            "order_item_id": item.id,
            "sequence": sequence,
        },
    )
    return DownloadGrant.objects.create(
        customer_account=order.customer_account,
        order_item=item,
        asset=asset,
        max_downloads=5,
        is_active=False,
    )


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
            active_assets = list(product.assets.filter(is_active=True))
            for asset in active_assets:
                DownloadGrant.objects.get_or_create(
                    customer_account=order.customer_account,
                    order_item=item,
                    asset=asset,
                    defaults={"max_downloads": 5, "is_active": True},
                )
            if not active_assets:
                existing_pending = DownloadGrant.objects.filter(
                    customer_account=order.customer_account,
                    order_item=item,
                    asset__metadata__pending_fulfillment=True,
                ).count()
                needed = max((item.quantity or 1) - existing_pending, 0)
                for offset in range(needed):
                    sequence = existing_pending + offset + 1
                    _create_pending_download_grant(
                        order,
                        item,
                        sequence,
                        reason="missing_digital_asset",
                    )

        if product.product_type == Product.ProductType.SERVICE:
            existing_count = FulfillmentOrder.objects.filter(order_item=item).count()
            needed = max((item.quantity or 1) - existing_count, 0)
            delivery_mode = _resolve_service_delivery_mode(item)
            service_offer = getattr(product, "service_offer", None)
            delivery_days = int(getattr(service_offer, "delivery_days", 0) or 0)
            due_at = now + timedelta(days=delivery_days) if delivery_days > 0 else None
            for offset in range(needed):
                sequence = existing_count + offset + 1
                download_grant = None
                if delivery_mode == FulfillmentOrder.DeliveryMode.DOWNLOADABLE:
                    download_grant = _create_pending_download_grant(
                        order,
                        item,
                        sequence,
                        reason="service_fulfillment",
                    )

                fulfillment_order = FulfillmentOrder.objects.create(
                    customer_account=order.customer_account,
                    order_item=item,
                    product=product,
                    status=FulfillmentOrder.Status.REQUESTED,
                    delivery_mode=delivery_mode,
                    customer_request=order.notes,
                    due_at=due_at,
                    download_grant=download_grant,
                    metadata={
                        "order_public_id": str(order.public_id),
                        "order_item_id": item.id,
                        "sequence": sequence,
                    },
                )
                send_fulfillment_order_requested_email(fulfillment_order)

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


def _backfill_subscriptions_from_webhook_history(account) -> None:
    event_types = [*SUBSCRIPTION_UPSERT_EVENT_TYPES, *SUBSCRIPTION_CANCELED_EVENT_TYPES]
    recent_events = list(
        WebhookEvent.objects.filter(
            provider=WebhookEvent.Provider.CLERK,
            event_type__in=event_types,
        )
        .order_by("-received_at")[:SUBSCRIPTION_BACKFILL_EVENT_LIMIT]
    )
    if not recent_events:
        return

    allowed_customer_ids = {
        str(account.profile.clerk_user_id or "").strip(),
        str(account.external_customer_id or "").strip(),
    }
    allowed_customer_emails = {
        str(account.billing_email or "").strip().lower(),
        str(account.profile.email or "").strip().lower(),
    }

    def _add_value(values: set[str], raw: object, *, lower: bool = False) -> None:
        normalized = str(raw or "").strip()
        if lower:
            normalized = normalized.lower()
        if normalized:
            values.add(normalized)

    def _payload_matches_account(data: dict[str, Any]) -> bool:
        candidate_ids: set[str] = set()
        candidate_emails: set[str] = set()

        def collect(payload_part: dict[str, Any]) -> None:
            for field in ("id", "user_id", "clerk_user_id", "customer_id", "subscriber_id", "payer_id"):
                _add_value(candidate_ids, payload_part.get(field))
            for field in ("email", "email_address", "billing_email"):
                _add_value(candidate_emails, payload_part.get(field), lower=True)

            nested_user = payload_part.get("user")
            if isinstance(nested_user, dict):
                collect(nested_user)

        collect(data)

        for nested_field in ("payer", "subscriber", "customer"):
            nested = data.get(nested_field)
            if isinstance(nested, dict):
                collect(nested)

        _add_value(candidate_ids, _extract_clerk_user_id_from_subscription_payload(data))

        return bool(
            (candidate_ids & allowed_customer_ids)
            or (candidate_emails & allowed_customer_emails)
        )

    for event in reversed(recent_events):
        payload = event.payload if isinstance(event.payload, dict) else {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if not isinstance(data, dict):
            continue

        if not _payload_matches_account(data):
            continue

        if event.event_type in SUBSCRIPTION_CANCELED_EVENT_TYPES:
            handle_billing_subscription_canceled(data)
        else:
            handle_billing_subscription_upsert(data)


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
        _backfill_subscriptions_from_webhook_history(account)
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


class AccountFulfillmentOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FulfillmentOrderSerializer

    def get_queryset(self):
        account = get_request_customer_account(self.request)
        return (
            FulfillmentOrder.objects.filter(customer_account=account)
            .select_related("product", "order_item", "download_grant", "download_grant__asset")
            .order_by("-created_at")
        )


class AccountBookingListCreateView(AccountFulfillmentOrderListView):
    """
    Deprecated endpoint alias.
    Keep GET compatibility for existing clients on /account/bookings/.
    """
