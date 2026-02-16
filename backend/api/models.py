from __future__ import annotations

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


class Profile(models.Model):
    class PlanTier(models.TextChoices):
        FREE = "free", "Free"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    clerk_user_id = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    image_url = models.URLField(blank=True)
    plan_tier = models.CharField(
        max_length=24,
        choices=PlanTier.choices,
        default=PlanTier.FREE,
    )
    billing_features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("plan_tier", "is_active"), name="profile_plan_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(plan_tier__in=("free", "pro", "enterprise")),
                name="profile_plan_tier_valid",
            ),
        ]

    @property
    def display_name(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email or self.clerk_user_id

    def __str__(self) -> str:
        return self.email or self.clerk_user_id


class Project(models.Model):
    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        BUILDING = "building", "Building"
        LIVE = "live", "Live"
        PAUSED = "paused", "Paused"

    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    summary = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IDEA,
    )
    monthly_recurring_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    target_launch_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("owner", "status"), name="project_owner_status_idx"),
            models.Index(fields=("owner", "updated_at"), name="project_owner_updated_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "slug"),
                name="project_owner_slug_unique",
            ),
            models.CheckConstraint(
                check=Q(monthly_recurring_revenue__gte=0),
                name="project_mrr_non_negative",
            ),
            models.CheckConstraint(
                check=~Q(name=""),
                name="project_name_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(slug=""),
                name="project_slug_not_empty",
            ),
        ]

    def clean(self) -> None:
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Project name cannot be empty."})

        self.slug = slugify((self.slug or "").strip() or self.name)
        if not self.slug:
            raise ValidationError({"slug": "Slug is required."})

        self.summary = (self.summary or "").strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.owner.clerk_user_id})"


class CustomerAccount(models.Model):
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="customer_account",
    )
    external_customer_id = models.CharField(max_length=128, blank=True, db_index=True)
    billing_email = models.EmailField(blank=True)
    full_name = models.CharField(max_length=180, blank=True)
    company_name = models.CharField(max_length=180, blank=True)
    country = models.CharField(max_length=2, blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def clean(self) -> None:
        self.external_customer_id = (self.external_customer_id or "").strip()
        self.billing_email = (self.billing_email or "").strip()
        self.full_name = (self.full_name or "").strip()
        self.company_name = (self.company_name or "").strip()
        self.country = (self.country or "").strip().upper()
        self.tax_id = (self.tax_id or "").strip()

        if self.country and len(self.country) != 2:
            raise ValidationError({"country": "Use a 2-letter ISO country code."})

    def save(self, *args, **kwargs):
        if not self.external_customer_id:
            self.external_customer_id = self.profile.clerk_user_id
        if not self.billing_email:
            self.billing_email = self.profile.email
        if not self.full_name:
            self.full_name = self.profile.display_name
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name or self.billing_email or self.external_customer_id


class Product(models.Model):
    class ProductType(models.TextChoices):
        DIGITAL = "digital", "Digital"
        SERVICE = "service", "Service"

    class Visibility(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="owned_products")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    tagline = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    product_type = models.CharField(
        max_length=24,
        choices=ProductType.choices,
        default=ProductType.DIGITAL,
    )
    visibility = models.CharField(
        max_length=24,
        choices=Visibility.choices,
        default=Visibility.DRAFT,
    )
    feature_keys = models.JSONField(default=list, blank=True)
    active_price = models.ForeignKey(
        "Price",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_for_products",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("owner", "visibility"), name="product_owner_visibility_idx"),
            models.Index(fields=("product_type", "visibility"), name="product_type_visibility_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("owner", "slug"), name="product_owner_slug_unique"),
            models.CheckConstraint(check=~Q(name=""), name="product_name_not_empty"),
            models.CheckConstraint(check=~Q(slug=""), name="product_slug_not_empty"),
        ]

    def clean(self) -> None:
        self.name = (self.name or "").strip()
        self.slug = slugify((self.slug or "").strip() or self.name)
        self.tagline = (self.tagline or "").strip()
        self.description = (self.description or "").strip()

        raw_features = self.feature_keys if isinstance(self.feature_keys, list) else []
        features: list[str] = []
        seen: set[str] = set()
        for feature in raw_features:
            normalized = str(feature or "").strip().lower().replace(" ", "_")
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            features.append(normalized)
        self.feature_keys = features

        if not self.name:
            raise ValidationError({"name": "Product name cannot be empty."})
        if not self.slug:
            raise ValidationError({"slug": "Slug is required."})
        if self.active_price and self.pk and self.active_price.product_id != self.pk:
            raise ValidationError({"active_price": "Active price must belong to this product."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Price(models.Model):
    class BillingPeriod(models.TextChoices):
        ONE_TIME = "one_time", "One-time"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    name = models.CharField(max_length=120, blank=True)
    amount_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    billing_period = models.CharField(
        max_length=20,
        choices=BillingPeriod.choices,
        default=BillingPeriod.ONE_TIME,
    )
    clerk_plan_id = models.CharField(max_length=128, blank=True, db_index=True)
    clerk_price_id = models.CharField(max_length=128, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("amount_cents", "created_at")
        indexes = [
            models.Index(fields=("product", "is_active"), name="price_product_active_idx"),
            models.Index(fields=("billing_period", "is_active"), name="price_period_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("product",),
                condition=Q(is_default=True),
                name="price_one_default_per_product",
            ),
        ]

    def clean(self) -> None:
        self.name = (self.name or "").strip()
        self.currency = (self.currency or "USD").strip().upper()
        self.clerk_plan_id = (self.clerk_plan_id or "").strip()
        self.clerk_price_id = (self.clerk_price_id or "").strip()

        if not self.currency or len(self.currency) != 3:
            raise ValidationError({"currency": "Currency must be a 3-letter code."})
        if self.is_default and not self.is_active:
            raise ValidationError({"is_default": "Default price must be active."})
        if self.amount_cents < 0:
            raise ValidationError({"amount_cents": "Amount cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        period = self.get_billing_period_display()
        return f"{self.product.name} {period} {self.amount_cents / 100:.2f} {self.currency}"


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
        CustomerAccount,
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
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    price = models.ForeignKey(
        Price,
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
        CustomerAccount,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    price = models.ForeignKey(
        Price,
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
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="transactions",
    )
    subscription = models.ForeignKey(
        Subscription,
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
        CustomerAccount,
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


class DigitalAsset(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="assets")
    title = models.CharField(max_length=180)
    file_path = models.CharField(max_length=420)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    version_label = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "id")
        indexes = [
            models.Index(fields=("product", "is_active"), name="asset_product_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("product", "file_path"), name="asset_product_path_unique"),
        ]

    def clean(self) -> None:
        self.title = (self.title or "").strip()
        self.file_path = (self.file_path or "").strip()
        self.checksum_sha256 = (self.checksum_sha256 or "").strip().lower()
        self.version_label = (self.version_label or "").strip()

        if not self.title:
            raise ValidationError({"title": "Asset title is required."})
        if not self.file_path:
            raise ValidationError({"file_path": "Asset path is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.product.name}: {self.title}"


class DownloadGrant(models.Model):
    token = models.UUIDField(default=uuid4, editable=False, unique=True, db_index=True)
    customer_account = models.ForeignKey(
        CustomerAccount,
        on_delete=models.CASCADE,
        related_name="download_grants",
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="download_grants",
    )
    asset = models.ForeignKey(DigitalAsset, on_delete=models.CASCADE, related_name="download_grants")
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


class ServiceOffer(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="service_offer")
    session_minutes = models.PositiveIntegerField(default=60)
    delivery_days = models.PositiveIntegerField(default=7)
    revision_count = models.PositiveIntegerField(default=0)
    onboarding_instructions = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def clean(self) -> None:
        if self.product and self.product.product_type != Product.ProductType.SERVICE:
            raise ValidationError({"product": "ServiceOffer requires a service product."})
        self.onboarding_instructions = (self.onboarding_instructions or "").strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"ServiceOffer({self.product.name})"


class Booking(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"

    customer_account = models.ForeignKey(
        CustomerAccount,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    service_offer = models.ForeignKey(
        ServiceOffer,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    order_item = models.ForeignKey(
        OrderItem,
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
