from django.urls import path

from .views import (
    BillingFeatureView,
    ClerkUserView,
    HealthView,
    MeView,
    ProfileView,
    ProjectDetailView,
    ProjectListCreateView,
    SupabaseProfileView,
)
from .webhooks import ClerkWebhookView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("me/", MeView.as_view(), name="me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("me/clerk/", ClerkUserView.as_view(), name="clerk-user"),
    path("billing/features/", BillingFeatureView.as_view(), name="billing-features"),
    path("projects/", ProjectListCreateView.as_view(), name="project-list"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("supabase/profile/", SupabaseProfileView.as_view(), name="supabase-profile"),
    path("webhooks/clerk/", ClerkWebhookView.as_view(), name="clerk-webhook"),
]
