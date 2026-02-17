from __future__ import annotations

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class AiUsageEvent(models.Model):
    class Metric(models.TextChoices):
        TOKENS = "tokens", "Tokens"
        IMAGES = "images", "Images"
        VIDEOS = "videos", "Videos"

    class Direction(models.TextChoices):
        INPUT = "input", "Input"
        OUTPUT = "output", "Output"
        TOTAL = "total", "Total"

    class Source(models.TextChoices):
        SIMULATOR = "simulator", "Simulator"
        OPENROUTER = "openrouter", "OpenRouter"
        OLLAMA = "ollama", "Ollama"
        MANUAL = "manual", "Manual"

    request_id = models.UUIDField(default=uuid4, editable=False, db_index=True)
    customer_account = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.CASCADE,
        related_name="ai_usage_events",
    )
    subscription = models.ForeignKey(
        "Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_usage_events",
    )
    metric = models.CharField(max_length=16, choices=Metric.choices)
    direction = models.CharField(max_length=16, choices=Direction.choices, default=Direction.TOTAL)
    amount = models.PositiveIntegerField(default=0)
    provider = models.CharField(max_length=32, blank=True)
    model_name = models.CharField(max_length=128, blank=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("customer_account", "metric", "created_at"), name="aiuse_cust_metric_created"),
            models.Index(
                fields=("customer_account", "metric", "period_start", "period_end"),
                name="aiuse_cust_metric_period",
            ),
        ]
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name="aiusage_amount_positive"),
            models.CheckConstraint(check=Q(period_end__gt=models.F("period_start")), name="aiusage_period_valid"),
        ]

    def clean(self) -> None:
        self.provider = str(self.provider or "").strip().lower()
        self.model_name = str(self.model_name or "").strip()
        if self.amount < 1:
            raise ValidationError({"amount": "Amount must be at least 1."})
        if self.period_end <= self.period_start:
            raise ValidationError({"period_end": "Period end must be after period start."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.customer_account_id}:{self.metric}:{self.amount}"
