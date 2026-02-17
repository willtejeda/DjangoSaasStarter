from django.contrib import admin

from .models import (
    Booking,
    CustomerAccount,
    DigitalAsset,
    DownloadGrant,
    Entitlement,
    FulfillmentOrder,
    Order,
    OrderItem,
    PaymentTransaction,
    Price,
    Product,
    Profile,
    Project,
    ServiceOffer,
    Subscription,
    WebhookEvent,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("clerk_user_id", "email", "plan_tier", "is_active", "updated_at")
    search_fields = ("clerk_user_id", "email", "first_name", "last_name")
    list_filter = ("plan_tier", "is_active")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "monthly_recurring_revenue", "updated_at")
    search_fields = ("name", "slug", "owner__email", "owner__clerk_user_id")
    list_filter = ("status",)


@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ("profile", "billing_email", "external_customer_id", "updated_at")
    search_fields = ("profile__clerk_user_id", "billing_email", "full_name", "external_customer_id")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "product_type", "visibility", "updated_at")
    search_fields = ("name", "slug", "owner__email", "owner__clerk_user_id")
    list_filter = ("product_type", "visibility")


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "amount_cents", "currency", "billing_period", "is_default", "is_active")
    search_fields = ("product__name", "name", "clerk_plan_id", "clerk_price_id")
    list_filter = ("billing_period", "currency", "is_default", "is_active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("public_id", "customer_account", "status", "total_cents", "currency", "updated_at")
    search_fields = ("public_id", "clerk_checkout_id", "external_reference", "customer_account__billing_email")
    list_filter = ("status", "currency")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "unit_amount_cents", "total_amount_cents")
    search_fields = ("order__public_id", "product__name", "product_name_snapshot")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "customer_account",
        "product",
        "status",
        "cancel_at_period_end",
        "current_period_end",
        "updated_at",
    )
    search_fields = ("customer_account__billing_email", "clerk_subscription_id", "product__name")
    list_filter = ("status", "cancel_at_period_end")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("provider", "external_id", "status", "amount_cents", "currency", "updated_at")
    search_fields = ("external_id", "order__public_id", "subscription__clerk_subscription_id")
    list_filter = ("provider", "status", "currency")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_id", "event_type", "status", "received_at", "processed_at")
    search_fields = ("event_id", "event_type")
    list_filter = ("provider", "status")


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ("customer_account", "feature_key", "source_type", "is_active", "ends_at", "updated_at")
    search_fields = ("customer_account__billing_email", "feature_key", "source_reference")
    list_filter = ("source_type", "is_active")


@admin.register(DigitalAsset)
class DigitalAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "file_path", "is_active", "updated_at")
    search_fields = ("title", "product__name", "file_path")
    list_filter = ("is_active",)


@admin.register(DownloadGrant)
class DownloadGrantAdmin(admin.ModelAdmin):
    list_display = ("token", "customer_account", "asset", "download_count", "max_downloads", "is_active")
    search_fields = ("token", "customer_account__billing_email", "asset__title")
    list_filter = ("is_active",)


@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = ("product", "session_minutes", "delivery_days", "revision_count", "updated_at")
    search_fields = ("product__name",)


@admin.register(FulfillmentOrder)
class FulfillmentOrderAdmin(admin.ModelAdmin):
    list_display = ("customer_account", "product", "status", "delivery_mode", "due_at", "updated_at")
    search_fields = ("customer_account__billing_email", "product__name", "shipping_tracking_number")
    list_filter = ("status", "delivery_mode")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("customer_account", "service_offer", "status", "scheduled_start", "scheduled_end")
    search_fields = ("customer_account__billing_email", "service_offer__product__name")
    list_filter = ("status",)
