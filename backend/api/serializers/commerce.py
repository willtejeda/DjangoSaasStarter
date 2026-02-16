from __future__ import annotations

from rest_framework import serializers

from ..models import (
    Booking,
    CustomerAccount,
    DownloadGrant,
    Entitlement,
    Order,
    OrderItem,
    Profile,
    ServiceOffer,
    Subscription,
)


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
