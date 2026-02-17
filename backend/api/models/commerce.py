from __future__ import annotations

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PAID = "paid", "Paid"
        FULFILLED = "fulfilled", "Fulfilled"
        CANCELED = "canceled", "Canceled"
        REFUNDED = "refunded", "Refunded"

    public_id = models.UUIDField(default=uuid4, editable=False, unique=True, db_index=True)
    customer_account = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )
    currency = models.CharField(max_length=3, default="USD")
    subtotal_cents = models.PositiveIntegerField(default=0)
    tax_cents = models.PositiveIntegerField(default=0)
    total_cents = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    clerk_checkout_id = models.CharField(max_length=128, blank=True, db_index=True)
    external_reference = models.CharField(max_length=128, blank=True, db_index=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    fulfilled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("customer_account", "status"), name="order_customer_status_idx"),
            models.Index(fields=("status", "updated_at"), name="order_status_updated_idx"),
        ]

    def clean(self) -> None:
        self.currency = (self.currency or "USD").strip().upper()
        self.notes = (self.notes or "").strip()
        self.clerk_checkout_id = (self.clerk_checkout_id or "").strip()
        self.external_reference = (self.external_reference or "").strip()

        if len(self.currency) != 3:
            raise ValidationError({"currency": "Currency must be a 3-letter code."})

        expected_total = (self.subtotal_cents or 0) + (self.tax_cents or 0)
        if self.total_cents != expected_total:
            raise ValidationError(
                {"total_cents": "Total must match subtotal + tax."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.public_id} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("Product", on_delete=models.PROTECT, related_name="order_items")
    price = models.ForeignKey(
        "Price",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_amount_cents = models.PositiveIntegerField(default=0)
    total_amount_cents = models.PositiveIntegerField(default=0)
    product_name_snapshot = models.CharField(max_length=180, blank=True)
    price_name_snapshot = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)
        indexes = [
            models.Index(fields=("order", "product"), name="order_item_order_product_idx"),
        ]

    def clean(self) -> None:
        if self.quantity < 1:
            raise ValidationError({"quantity": "Quantity must be at least 1."})
        if self.price and self.price.product_id != self.product_id:
            raise ValidationError({"price": "Price must belong to the selected product."})

        if not self.product_name_snapshot:
            self.product_name_snapshot = (self.product.name if self.product_id else "").strip()
        self.price_name_snapshot = (self.price_name_snapshot or "").strip()
        if not self.price_name_snapshot and self.price_id:
            self.price_name_snapshot = (self.price.name or self.price.get_billing_period_display()).strip()

        self.total_amount_cents = (self.unit_amount_cents or 0) * (self.quantity or 0)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.product_name_snapshot} x{self.quantity}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        INCOMPLETE = "incomplete", "Incomplete"
        PAUSED = "paused", "Paused"

    customer_account = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    price = models.ForeignKey(
        "Price",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INCOMPLETE)
    clerk_subscription_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("customer_account", "status"), name="sub_customer_status_idx"),
        ]

    def clean(self) -> None:
        self.clerk_subscription_id = (self.clerk_subscription_id or "").strip() or None

        if self.price_id and self.product_id and self.price.product_id != self.product_id:
            raise ValidationError({"price": "Price must belong to the selected product."})

        if (
            self.current_period_start
            and self.current_period_end
            and self.current_period_end <= self.current_period_start
        ):
            raise ValidationError({"current_period_end": "Must be after current_period_start."})

    def save(self, *args, **kwargs):
        if self.price_id and not self.product_id:
            self.product = self.price.product
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.clerk_subscription_id or f"subscription-{self.pk}"


class PaymentTransaction(models.Model):
    class Provider(models.TextChoices):
        CLERK = "clerk", "Clerk"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELED = "canceled", "Canceled"

    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="transactions",
    )
    subscription = models.ForeignKey(
        "Subscription",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="transactions",
    )
    provider = models.CharField(max_length=24, choices=Provider.choices, default=Provider.CLERK)
    external_id = models.CharField(max_length=128, blank=True, db_index=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    amount_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("provider", "external_id"), name="txn_provider_external_idx"),
            models.Index(fields=("status", "updated_at"), name="txn_status_updated_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(order__isnull=False) | Q(subscription__isnull=False),
                name="txn_order_or_sub_required",
            ),
        ]

    def clean(self) -> None:
        self.external_id = (self.external_id or "").strip()
        self.currency = (self.currency or "USD").strip().upper()
        if len(self.currency) != 3:
            raise ValidationError({"currency": "Currency must be a 3-letter code."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.external_id or f"transaction-{self.pk}"


class WebhookEvent(models.Model):
    class Provider(models.TextChoices):
        CLERK = "clerk", "Clerk"
        STRIPE = "stripe", "Stripe"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        IGNORED = "ignored", "Ignored"

    provider = models.CharField(max_length=24, choices=Provider.choices, default=Provider.CLERK)
    event_id = models.CharField(max_length=191)
    event_type = models.CharField(max_length=191)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.RECEIVED)
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-received_at",)
        constraints = [
            models.UniqueConstraint(fields=("provider", "event_id"), name="webhook_provider_event_unique"),
        ]
        indexes = [
            models.Index(fields=("status", "received_at"), name="webhook_status_received_idx"),
        ]

    def clean(self) -> None:
        self.event_id = (self.event_id or "").strip()
        self.event_type = (self.event_type or "").strip()
        self.error_message = (self.error_message or "").strip()

        if not self.event_id:
            raise ValidationError({"event_id": "Event id is required."})
        if not self.event_type:
            raise ValidationError({"event_type": "Event type is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_id}"


class Entitlement(models.Model):
    class SourceType(models.TextChoices):
        PLAN = "plan", "Plan"
        PURCHASE = "purchase", "Purchase"
        MANUAL = "manual", "Manual"

    customer_account = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.CASCADE,
        related_name="entitlements",
    )
    feature_key = models.CharField(max_length=80, db_index=True)
    source_type = models.CharField(max_length=24, choices=SourceType.choices, default=SourceType.PURCHASE)
    source_reference = models.CharField(max_length=128, blank=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("customer_account", "feature_key", "source_type", "source_reference"),
                name="entitlement_source_unique",
            ),
        ]
        indexes = [
            models.Index(fields=("customer_account", "is_active"), name="entitlement_cust_active_idx"),
            models.Index(fields=("feature_key", "is_active"), name="entitlement_feature_active_idx"),
        ]

    @property
    def is_current(self) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at <= now:
            return False
        return True

    def clean(self) -> None:
        normalized_feature = str(self.feature_key or "").strip().lower().replace(" ", "_")
        if not normalized_feature:
            raise ValidationError({"feature_key": "Feature key is required."})
        self.feature_key = normalized_feature
        self.source_reference = (self.source_reference or "").strip()

        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "End timestamp must be after starts_at."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.customer_account_id}:{self.feature_key}"


class DownloadGrant(models.Model):
    token = models.UUIDField(default=uuid4, editable=False, unique=True, db_index=True)
    customer_account = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.CASCADE,
        related_name="download_grants",
    )
    order_item = models.ForeignKey(
        "OrderItem",
        on_delete=models.CASCADE,
        related_name="download_grants",
    )
    asset = models.ForeignKey("DigitalAsset", on_delete=models.CASCADE, related_name="download_grants")
    expires_at = models.DateTimeField(blank=True, null=True)
    max_downloads = models.PositiveIntegerField(default=5)
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("customer_account", "is_active"), name="grant_customer_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("order_item", "asset"), name="grant_order_item_asset_unique"),
        ]

    @property
    def can_download(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() >= self.expires_at:
            return False
        if self.max_downloads and self.download_count >= self.max_downloads:
            return False
        return True

    def clean(self) -> None:
        if self.max_downloads and self.max_downloads < 1:
            raise ValidationError({"max_downloads": "max_downloads must be at least 1."})
        if self.order_item_id and self.asset_id and self.order_item.product_id != self.asset.product_id:
            raise ValidationError(
                {"asset": "Download asset must belong to the same product as order item."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.token)


class FulfillmentOrder(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        IN_PROGRESS = "in_progress", "In progress"
        READY_FOR_DELIVERY = "ready_for_delivery", "Ready for delivery"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"

    class DeliveryMode(models.TextChoices):
        DOWNLOADABLE = "downloadable", "Downloadable"
        PHYSICAL_SHIPPED = "physical_shipped", "Physical shipped"

    customer_account = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.CASCADE,
        related_name="fulfillment_orders",
    )
    order_item = models.ForeignKey(
        "OrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfillment_orders",
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfillment_orders",
    )
    download_grant = models.OneToOneField(
        "DownloadGrant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfillment_order",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.REQUESTED)
    delivery_mode = models.CharField(
        max_length=24,
        choices=DeliveryMode.choices,
        default=DeliveryMode.DOWNLOADABLE,
    )
    customer_request = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    due_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    shipping_carrier = models.CharField(max_length=120, blank=True)
    shipping_tracking_number = models.CharField(max_length=120, blank=True)
    shipping_tracking_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("customer_account", "status"), name="fulfill_cust_status_idx"),
            models.Index(fields=("delivery_mode", "status"), name="fulfill_mode_status_idx"),
        ]

    def clean(self) -> None:
        self.customer_request = (self.customer_request or "").strip()
        self.delivery_notes = (self.delivery_notes or "").strip()
        self.internal_notes = (self.internal_notes or "").strip()
        self.shipping_carrier = (self.shipping_carrier or "").strip()
        self.shipping_tracking_number = (self.shipping_tracking_number or "").strip()
        self.shipping_tracking_url = (self.shipping_tracking_url or "").strip()

        if self.order_item_id and self.product_id and self.order_item.product_id != self.product_id:
            raise ValidationError({"product": "Product must match the linked order item product."})

        if self.download_grant_id:
            if self.delivery_mode != self.DeliveryMode.DOWNLOADABLE:
                raise ValidationError({"download_grant": "Download grant can only be set for downloadable fulfillment orders."})
            if self.order_item_id and self.download_grant.order_item_id != self.order_item_id:
                raise ValidationError({"download_grant": "Download grant must belong to the same order item."})

        if self.delivery_mode == self.DeliveryMode.PHYSICAL_SHIPPED and self.download_grant_id:
            raise ValidationError({"delivery_mode": "Physical shipment cannot include a download grant."})

        if self.completed_at and self.status not in {self.Status.COMPLETED, self.Status.CANCELED}:
            raise ValidationError({"completed_at": "completed_at can only be set when status is completed or canceled."})

    def save(self, *args, **kwargs):
        if self.order_item_id and not self.product_id:
            self.product = self.order_item.product
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"FulfillmentOrder({self.customer_account_id}, {self.status}, {self.delivery_mode})"


class Booking(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"

    customer_account = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    service_offer = models.ForeignKey(
        "ServiceOffer",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    order_item = models.ForeignKey(
        "OrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.REQUESTED)
    scheduled_start = models.DateTimeField(blank=True, null=True)
    scheduled_end = models.DateTimeField(blank=True, null=True)
    meeting_url = models.URLField(blank=True)
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("customer_account", "status"), name="booking_customer_status_idx"),
            models.Index(fields=("scheduled_start",), name="booking_scheduled_start_idx"),
        ]

    def clean(self) -> None:
        self.meeting_url = (self.meeting_url or "").strip()
        self.customer_notes = (self.customer_notes or "").strip()
        self.internal_notes = (self.internal_notes or "").strip()

        if self.scheduled_start and self.scheduled_end and self.scheduled_end <= self.scheduled_start:
            raise ValidationError({"scheduled_end": "scheduled_end must be after scheduled_start."})

        if self.order_item_id and self.order_item.product_id != self.service_offer.product_id:
            raise ValidationError({"order_item": "Order item product must match service offer product."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Booking({self.customer_account_id}, {self.service_offer_id}, {self.status})"
