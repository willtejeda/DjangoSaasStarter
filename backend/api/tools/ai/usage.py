from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import APIException

from ...models import AiUsageEvent, CustomerAccount, Subscription


class UsageLimitExceeded(APIException):
    status_code = 429
    default_code = "usage_limit_exceeded"
    default_detail = "Usage limit exceeded for the current billing cycle."


@dataclass(frozen=True)
class UsagePeriod:
    start: datetime
    end: datetime
    source: str
    subscription_id: int | None


def _month_rollover(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _anchored_dt(year: int, month: int, anchor: datetime) -> datetime:
    last_day = calendar.monthrange(year, month)[1]
    day = min(anchor.day, last_day)
    return datetime(
        year=year,
        month=month,
        day=day,
        hour=anchor.hour,
        minute=anchor.minute,
        second=anchor.second,
        microsecond=anchor.microsecond,
        tzinfo=anchor.tzinfo,
    )


def _resolve_anchored_monthly_period(account: CustomerAccount, now: datetime) -> UsagePeriod:
    anchor = account.created_at.astimezone(now.tzinfo) if account.created_at.tzinfo else account.created_at
    this_month_anchor = _anchored_dt(now.year, now.month, anchor)

    if now < this_month_anchor:
        prev_year, prev_month = _prev_month(now.year, now.month)
        period_start = _anchored_dt(prev_year, prev_month, anchor)
    else:
        period_start = this_month_anchor

    next_year, next_month = _month_rollover(period_start.year, period_start.month)
    period_end = _anchored_dt(next_year, next_month, anchor)
    return UsagePeriod(
        start=period_start,
        end=period_end,
        source="anchored_monthly_cycle",
        subscription_id=None,
    )


def resolve_usage_period(account: CustomerAccount, now: datetime) -> UsagePeriod:
    subscriptions = Subscription.objects.filter(
        customer_account=account,
        status__in=[
            Subscription.Status.ACTIVE,
            Subscription.Status.TRIALING,
            Subscription.Status.PAST_DUE,
        ],
    ).order_by("-current_period_end", "-updated_at")

    for subscription in subscriptions:
        start = subscription.current_period_start
        end = subscription.current_period_end
        if not start or not end or end <= start:
            continue
        if start <= now < end:
            return UsagePeriod(
                start=start,
                end=end,
                source="subscription_cycle",
                subscription_id=subscription.id,
            )

    return _resolve_anchored_monthly_period(account, now)


def get_plan_limits(plan_tier: str) -> dict[str, int | None]:
    limits_by_plan = {
        "free": {
            "tokens": int(getattr(settings, "AI_USAGE_LIMIT_FREE_TOKENS", 100000)),
            "images": int(getattr(settings, "AI_USAGE_LIMIT_FREE_IMAGES", 120)),
            "videos": int(getattr(settings, "AI_USAGE_LIMIT_FREE_VIDEOS", 2)),
        },
        "pro": {
            "tokens": int(getattr(settings, "AI_USAGE_LIMIT_PRO_TOKENS", 1500000)),
            "images": int(getattr(settings, "AI_USAGE_LIMIT_PRO_IMAGES", 1000)),
            "videos": int(getattr(settings, "AI_USAGE_LIMIT_PRO_VIDEOS", 40)),
        },
        "enterprise": {
            "tokens": None,
            "images": None,
            "videos": None,
        },
    }
    return limits_by_plan.get(plan_tier, limits_by_plan["free"])


def get_usage_totals(account: CustomerAccount, period: UsagePeriod) -> dict[str, int]:
    rows = (
        AiUsageEvent.objects.filter(
            customer_account=account,
            created_at__gte=period.start,
            created_at__lt=period.end,
        )
        .values("metric")
        .annotate(total=Sum("amount"))
    )
    totals = {"tokens": 0, "images": 0, "videos": 0}
    for row in rows:
        metric = str(row.get("metric") or "")
        if metric in totals:
            totals[metric] = int(row.get("total") or 0)
    return totals


def consume_usage_events(
    *,
    account: CustomerAccount,
    plan_tier: str,
    period: UsagePeriod,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    if not events:
        return {"totals": get_usage_totals(account, period), "limits": get_plan_limits(plan_tier)}

    by_metric_requested: dict[str, int] = defaultdict(int)
    for event in events:
        metric = str(event.get("metric") or "").strip().lower()
        amount = int(event.get("amount") or 0)
        if metric not in {"tokens", "images", "videos"} or amount < 1:
            continue
        by_metric_requested[metric] += amount

    limits = get_plan_limits(plan_tier)
    enforce_limits = bool(getattr(settings, "AI_USAGE_ENFORCEMENT_ENABLED", True))

    with transaction.atomic():
        # Lock account row so checks + inserts are serialized.
        CustomerAccount.objects.select_for_update().get(pk=account.pk)
        existing_totals = get_usage_totals(account, period)

        if enforce_limits:
            for metric, requested in by_metric_requested.items():
                limit = limits.get(metric)
                used = existing_totals.get(metric, 0)
                if limit is None:
                    continue
                remaining = max(limit - used, 0)
                if requested > remaining:
                    raise UsageLimitExceeded(
                        detail=(
                            f"{metric} quota exceeded for current cycle. "
                            f"Requested {requested}, remaining {remaining}, "
                            f"resets at {period.end.isoformat()}."
                        )
                    )

        for raw_event in events:
            metric = str(raw_event.get("metric") or "").strip().lower()
            amount = int(raw_event.get("amount") or 0)
            if metric not in {"tokens", "images", "videos"} or amount < 1:
                continue

            request_id = raw_event.get("request_id") or uuid4()
            AiUsageEvent.objects.create(
                request_id=request_id,
                customer_account=account,
                subscription_id=period.subscription_id,
                metric=metric,
                direction=str(raw_event.get("direction") or AiUsageEvent.Direction.TOTAL),
                amount=amount,
                provider=str(raw_event.get("provider") or "").strip().lower(),
                model_name=str(raw_event.get("model_name") or "").strip(),
                period_start=period.start,
                period_end=period.end,
                metadata=raw_event.get("metadata") if isinstance(raw_event.get("metadata"), dict) else {},
            )

        updated_totals = get_usage_totals(account, period)

    return {"totals": updated_totals, "limits": limits}
