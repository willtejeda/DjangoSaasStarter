from __future__ import annotations

from django.utils.text import slugify
from rest_framework import serializers

from ..models import Profile, Project


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
