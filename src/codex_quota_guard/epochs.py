from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Epoch, Sample


@dataclass(frozen=True, slots=True)
class EpochDecision:
    starts_new_epoch: bool
    reason: str | None = None


def decide_epoch(previous: Sample | None, current: Sample) -> EpochDecision:
    if previous is None:
        return EpochDecision(True, "first_sample")
    if current.timestamp <= previous.timestamp:
        return EpochDecision(False, "old_or_duplicate_sample")
    if previous.limit_id != current.limit_id:
        return EpochDecision(True, "limit_identity_changed")
    if previous.duration_minutes != current.duration_minutes:
        return EpochDecision(True, "window_duration_changed")
    if previous.resets_at and current.resets_at:
        delta = abs((current.resets_at - previous.resets_at).total_seconds())
        if delta > 120:
            return EpochDecision(True, "reset_at_changed")
    if previous.used_percent >= 90.0 and current.used_percent <= 5.0:
        return EpochDecision(True, "percent_wrapped")
    return EpochDecision(False)


def new_epoch(sample: Sample, reason: str) -> Epoch:
    return Epoch(
        id=None,
        window_type=sample.window_type,
        provider=sample.provider,
        limit_id=sample.limit_id,
        started_at=sample.timestamp,
        reset_at=sample.resets_at,
        duration_minutes=sample.duration_minutes,
        first_percent=sample.used_percent,
        last_percent=sample.used_percent,
        reset_reason=reason,
    )


def complete_epoch(epoch: Epoch, ended_at: datetime, reason: str) -> None:
    epoch.completed = True
    epoch.ended_at = ended_at
    epoch.reset_reason = reason
