from django.db import models


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
        unique_together = ("owner", "slug")
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return f"{self.name} ({self.owner.clerk_user_id})"
