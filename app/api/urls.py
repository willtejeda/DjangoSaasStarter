from django.urls import path

from .views import BillingFeatureView, ClerkUserView, HealthView, MeView, SupabaseProfileView
from .webhooks import ClerkWebhookView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("me/", MeView.as_view(), name="me"),
    path("me/clerk/", ClerkUserView.as_view(), name="clerk-user"),
    path("billing/features/", BillingFeatureView.as_view(), name="billing-features"),
    path("supabase/profile/", SupabaseProfileView.as_view(), name="supabase-profile"),
    path("webhooks/clerk/", ClerkWebhookView.as_view(), name="clerk-webhook"),
]
