from __future__ import annotations

from django.utils.text import slugify
from rest_framework import serializers

from .models import Profile, Project


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

    def validate_slug(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("Slug cannot be empty.")
        return slugify(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        name = attrs.get("name")
        if not attrs.get("slug"):
            attrs["slug"] = slugify(name or "")
        if not attrs.get("slug"):
            raise serializers.ValidationError({"slug": "Slug is required."})
        return attrs
