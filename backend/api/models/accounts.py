from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify


class Profile(models.Model):
    class PlanTier(models.TextChoices):
        FREE = "free", "Free"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    clerk_user_id = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    image_url = models.URLField(blank=True)
    plan_tier = models.CharField(
        max_length=24,
        choices=PlanTier.choices,
        default=PlanTier.FREE,
    )
    billing_features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("plan_tier", "is_active"), name="profile_plan_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(plan_tier__in=("free", "pro", "enterprise")),
                name="profile_plan_tier_valid",
            ),
        ]

    @property
    def display_name(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email or self.clerk_user_id

    def __str__(self) -> str:
        return self.email or self.clerk_user_id


class Project(models.Model):
    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        BUILDING = "building", "Building"
        LIVE = "live", "Live"
        PAUSED = "paused", "Paused"

    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    summary = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IDEA,
    )
    monthly_recurring_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    target_launch_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("owner", "status"), name="project_owner_status_idx"),
            models.Index(fields=("owner", "updated_at"), name="project_owner_updated_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "slug"),
                name="project_owner_slug_unique",
            ),
            models.CheckConstraint(
                check=Q(monthly_recurring_revenue__gte=0),
                name="project_mrr_non_negative",
            ),
            models.CheckConstraint(
                check=~Q(name=""),
                name="project_name_not_empty",
            ),
            models.CheckConstraint(
                check=~Q(slug=""),
                name="project_slug_not_empty",
            ),
        ]

    def clean(self) -> None:
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Project name cannot be empty."})

        self.slug = slugify((self.slug or "").strip() or self.name)
        if not self.slug:
            raise ValidationError({"slug": "Slug is required."})

        self.summary = (self.summary or "").strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.owner.clerk_user_id})"


class CustomerAccount(models.Model):
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="customer_account",
    )
    external_customer_id = models.CharField(max_length=128, blank=True, db_index=True)
    billing_email = models.EmailField(blank=True)
    full_name = models.CharField(max_length=180, blank=True)
    company_name = models.CharField(max_length=180, blank=True)
    country = models.CharField(max_length=2, blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def clean(self) -> None:
        self.external_customer_id = (self.external_customer_id or "").strip()
        self.billing_email = (self.billing_email or "").strip()
        self.full_name = (self.full_name or "").strip()
        self.company_name = (self.company_name or "").strip()
        self.country = (self.country or "").strip().upper()
        self.tax_id = (self.tax_id or "").strip()

        if self.country and len(self.country) != 2:
            raise ValidationError({"country": "Use a 2-letter ISO country code."})

    def save(self, *args, **kwargs):
        if not self.external_customer_id:
            self.external_customer_id = self.profile.clerk_user_id
        if not self.billing_email:
            self.billing_email = self.profile.email
        if not self.full_name:
            self.full_name = self.profile.display_name
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name or self.billing_email or self.external_customer_id
