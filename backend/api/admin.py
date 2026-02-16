from django.contrib import admin

from .models import Profile, Project


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
