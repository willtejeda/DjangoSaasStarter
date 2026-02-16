from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify


class Product(models.Model):
    class ProductType(models.TextChoices):
        DIGITAL = "digital", "Digital"
        SERVICE = "service", "Service"

    class Visibility(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    owner = models.ForeignKey("Profile", on_delete=models.CASCADE, related_name="owned_products")
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
