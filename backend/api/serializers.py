from __future__ import annotations

from django.utils.text import slugify
from rest_framework import serializers

from .models import (
    Booking,
    CustomerAccount,
    DigitalAsset,
    DownloadGrant,
    Entitlement,
    Order,
    OrderItem,
    Price,
    Product,
    Profile,
    Project,
    ServiceOffer,
    Subscription,
)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "id",
            "clerk_user_id",
            "email",
            "first_name",
            "last_name",
            "image_url",
            "plan_tier",
            "billing_features",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProjectSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "slug",
            "summary",
            "status",
            "monthly_recurring_revenue",
            "target_launch_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("Name cannot be empty.")
        return cleaned

    def validate_slug(self, value: str) -> str:
        return slugify(value or "")

    def validate_monthly_recurring_revenue(self, value):
        if value < 0:
            raise serializers.ValidationError("MRR cannot be negative.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        effective_name = attrs.get("name", getattr(instance, "name", ""))
        effective_slug = attrs.get("slug", getattr(instance, "slug", ""))
        if not effective_slug:
            effective_slug = slugify(effective_name or "")
        else:
            effective_slug = slugify(effective_slug)

        attrs["slug"] = effective_slug
        if not attrs.get("slug"):
            raise serializers.ValidationError({"slug": "Slug is required."})
        return attrs


class PublicPriceSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Price
        fields = (
            "id",
            "name",
            "amount_cents",
            "amount",
            "currency",
            "billing_period",
            "is_default",
        )

    def get_amount(self, obj: Price) -> str:
        return f"{obj.amount_cents / 100:.2f}"


class PublicDigitalAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalAsset
        fields = (
            "id",
            "title",
            "version_label",
            "file_size_bytes",
        )


class ServiceOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOffer
        fields = (
            "id",
            "session_minutes",
            "delivery_days",
            "revision_count",
            "onboarding_instructions",
            "metadata",
        )


class ProductListSerializer(serializers.ModelSerializer):
    active_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "tagline",
            "description",
            "product_type",
            "visibility",
            "feature_keys",
            "active_price",
            "created_at",
            "updated_at",
        )

    def get_active_price(self, obj: Product):
        selected = obj.active_price
        if selected is None:
            selected = obj.prices.filter(is_active=True, is_default=True).order_by("id").first()
        if selected is None:
            selected = obj.prices.filter(is_active=True).order_by("amount_cents", "id").first()
        return PublicPriceSerializer(selected).data if selected else None


class ProductDetailSerializer(ProductListSerializer):
    prices = PublicPriceSerializer(many=True, read_only=True)
    assets = serializers.SerializerMethodField()
    service_offer = ServiceOfferSerializer(read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "prices",
            "assets",
            "service_offer",
            "metadata",
        )

    def get_assets(self, obj: Product):
        queryset = obj.assets.filter(is_active=True)
        return PublicDigitalAssetSerializer(queryset, many=True).data


class SellerPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = (
            "id",
            "product",
            "name",
            "amount_cents",
            "currency",
            "billing_period",
            "clerk_plan_id",
            "clerk_price_id",
            "is_active",
            "is_default",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_currency(self, value: str) -> str:
        cleaned = (value or "").strip().upper()
        if len(cleaned) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter code.")
        return cleaned


class SellerAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalAsset
        fields = (
            "id",
            "product",
            "title",
            "file_path",
            "file_size_bytes",
            "checksum_sha256",
            "version_label",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class SellerProductSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False, allow_blank=True)
    prices = SellerPriceSerializer(many=True, read_only=True)
    assets = SellerAssetSerializer(many=True, read_only=True)
    service_offer = ServiceOfferSerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "tagline",
            "description",
            "product_type",
            "visibility",
            "feature_keys",
            "active_price",
            "metadata",
            "prices",
            "assets",
            "service_offer",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("Name cannot be empty.")
        return cleaned

    def validate_slug(self, value: str) -> str:
        return slugify(value or "")

    def validate_feature_keys(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("feature_keys must be an array of feature keys.")

        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            key = str(item or "").strip().lower().replace(" ", "_")
            if not key or key in seen:
                continue
            seen.add(key)
            normalized.append(key)
        return normalized

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        name = attrs.get("name", getattr(instance, "name", ""))
        slug = attrs.get("slug", getattr(instance, "slug", ""))
        attrs["slug"] = slugify(slug or name or "")
        if not attrs["slug"]:
            raise serializers.ValidationError({"slug": "Slug is required."})

        active_price = attrs.get("active_price")
        if active_price is None:
            return attrs

        product_id = instance.id if instance else None
        if product_id is not None and active_price.product_id != product_id:
            raise serializers.ValidationError({"active_price": "Active price must belong to this product."})
        return attrs


class LightweightProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id", "clerk_user_id", "email", "first_name", "last_name")


class CustomerAccountSerializer(serializers.ModelSerializer):
    profile = LightweightProfileSerializer(read_only=True)

    class Meta:
        model = CustomerAccount
        fields = (
            "id",
            "profile",
            "external_customer_id",
            "billing_email",
            "full_name",
            "company_name",
            "country",
            "tax_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "profile", "external_customer_id", "created_at", "updated_at")


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_type = serializers.CharField(source="product.product_type", read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "product_slug",
            "product_type",
            "price",
            "quantity",
            "unit_amount_cents",
            "total_amount_cents",
            "product_name_snapshot",
            "price_name_snapshot",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "unit_amount_cents",
            "total_amount_cents",
            "product_name_snapshot",
            "price_name_snapshot",
            "created_at",
            "updated_at",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "public_id",
            "status",
            "currency",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "notes",
            "clerk_checkout_id",
            "external_reference",
            "paid_at",
            "fulfilled_at",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "public_id",
            "status",
            "currency",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "clerk_checkout_id",
            "external_reference",
            "paid_at",
            "fulfilled_at",
            "items",
            "created_at",
            "updated_at",
        )


class OrderCreateSerializer(serializers.Serializer):
    price_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)


class OrderConfirmSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["clerk", "manual"], default="clerk")
    external_id = serializers.CharField(required=False, allow_blank=True, max_length=128)
    clerk_checkout_id = serializers.CharField(required=False, allow_blank=True, max_length=128)
    raw_payload = serializers.JSONField(required=False)


class SubscriptionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    price_summary = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            "id",
            "product",
            "product_name",
            "price",
            "price_summary",
            "status",
            "clerk_subscription_id",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "canceled_at",
            "metadata",
            "created_at",
            "updated_at",
        )

    def get_price_summary(self, obj: Subscription):
        if not obj.price_id:
            return None
        return {
            "id": obj.price.id,
            "name": obj.price.name,
            "amount_cents": obj.price.amount_cents,
            "currency": obj.price.currency,
            "billing_period": obj.price.billing_period,
        }


class EntitlementSerializer(serializers.ModelSerializer):
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = Entitlement
        fields = (
            "id",
            "feature_key",
            "source_type",
            "source_reference",
            "starts_at",
            "ends_at",
            "is_active",
            "is_current",
            "metadata",
            "created_at",
            "updated_at",
        )


class DownloadGrantSerializer(serializers.ModelSerializer):
    can_download = serializers.BooleanField(read_only=True)
    asset_title = serializers.CharField(source="asset.title", read_only=True)
    product_name = serializers.CharField(source="asset.product.name", read_only=True)

    class Meta:
        model = DownloadGrant
        fields = (
            "id",
            "token",
            "asset",
            "asset_title",
            "product_name",
            "order_item",
            "expires_at",
            "max_downloads",
            "download_count",
            "last_downloaded_at",
            "is_active",
            "can_download",
            "created_at",
            "updated_at",
        )


class BookingSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="service_offer.product.name", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "service_offer",
            "product_name",
            "order_item",
            "status",
            "scheduled_start",
            "scheduled_end",
            "meeting_url",
            "customer_notes",
            "internal_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "meeting_url",
            "internal_notes",
            "created_at",
            "updated_at",
        )


class ServiceOfferUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOffer
        fields = (
            "id",
            "product",
            "session_minutes",
            "delivery_days",
            "revision_count",
            "onboarding_instructions",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
