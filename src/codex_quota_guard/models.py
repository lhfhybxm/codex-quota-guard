from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class UsageUnit(StrEnum):
    CREDITS = "credits"
    TOKENS = "tokens"
    API_USD = "api_usd"
    UNKNOWN = "unknown"


class WindowType(StrEnum):
    FIVE_HOUR = "five_hour"
    WEEKLY = "weekly"


class EstimateStatus(StrEnum):
    READY = "ready"
    WARMING_UP = "warming_up"
    UNAVAILABLE = "unavailable"


class Freshness(StrEnum):
    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class WindowSnapshot:
    window_type: WindowType
    used_percent: float
    resets_at: datetime | None
    duration_minutes: int | None
    limit_id: str | None
    limit_name: str | None = None


@dataclass(frozen=True, slots=True)
class AccountUsage:
    supported: bool
    lifetime_tokens: int | None = None
    daily_buckets: tuple[tuple[str, int], ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class QuotaSnapshot:
    timestamp: datetime
    provider: str
    windows: dict[WindowType, WindowSnapshot]
    account_usage: AccountUsage
    plan_type: str | None = None
    purchased_credits_balance: str | None = None
    has_purchased_credits: bool | None = None
    purchased_credits_unlimited: bool | None = None
    source_version: str | None = None


@dataclass(frozen=True, slots=True)
class Sample:
    window_type: WindowType
    timestamp: datetime
    used_percent: float
    resets_at: datetime | None
    duration_minutes: int | None
    cumulative_usage: float | None
    usage_unit: UsageUnit
    provider: str
    limit_id: str | None = None
    model: str | None = None
    estimated_credits: float | None = None
    cost_usd: float | None = None
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    source_signature: str | None = None
    received_at: datetime | None = None
    stale: bool = False

    @property
    def delay_seconds(self) -> float:
        if self.received_at is None:
            return 0.0
        return max(0.0, (self.received_at - self.timestamp).total_seconds())


@dataclass(slots=True)
class Epoch:
    id: int | None
    window_type: WindowType
    provider: str
    limit_id: str | None
    started_at: datetime
    reset_at: datetime | None
    duration_minutes: int | None
    first_percent: float
    last_percent: float
    completed: bool = False
    ended_at: datetime | None = None
    reset_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Estimate:
    status: EstimateStatus
    unit: UsageUnit
    total: float | None
    used: float | None
    remaining: float | None
    lower_bound: float | None
    upper_bound: float | None
    confidence: int
    confidence_label: str
    sample_count: int
    percent_span: float
    slope_per_percent: float | None
    intercept: float | None
    residual_mad: float | None
    reason: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HistoricalBaseline:
    unit: UsageUnit
    median_total: float
    robust_spread: float
    epoch_count: int


@dataclass(frozen=True, slots=True)
class QuotaChangeAlert:
    previous: float
    current: float
    percent_change: float
    message: str


@dataclass(slots=True)
class ProviderHealth:
    provider: str
    last_success: datetime | None = None
    last_failure: datetime | None = None
    failure_class: str | None = None
    consecutive_failures: int = 0
    backoff_until: datetime | None = None
    status: Freshness = Freshness.UNAVAILABLE
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CollectionResult:
    snapshot: QuotaSnapshot | None
    samples: tuple[Sample, ...] = ()
    estimates: dict[WindowType, Estimate] = field(default_factory=dict)
    health: ProviderHealth | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EpochSummary:
    id: int
    window_type: WindowType
    started_at: datetime
    ended_at: datetime | None
    first_percent: float
    last_percent: float
    estimated_total: float | None
    confidence: int | None
    lower_bound: float | None
    upper_bound: float | None
    unit: UsageUnit
    completed: bool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def datetime_to_text(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def datetime_from_text(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def unix_seconds_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None
