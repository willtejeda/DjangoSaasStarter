from __future__ import annotations

from django.utils.text import slugify
from rest_framework import serializers

from ..models import DigitalAsset, Price, Product, ServiceOffer


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
