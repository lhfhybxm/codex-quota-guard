from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from typing import Iterable, Sequence

from .models import (
    Estimate,
    EstimateStatus,
    HistoricalBaseline,
    QuotaChangeAlert,
    Sample,
    UsageUnit,
)


MIN_PERCENT_SPAN = 5.0
MIN_USEFUL_SAMPLES = 3


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _median(values: Sequence[float]) -> float:
    return float(statistics.median(values))


def _mad(values: Sequence[float], center: float | None = None) -> float:
    if not values:
        return 0.0
    center = _median(values) if center is None else center
    return _median([abs(value - center) for value in values])


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _rounded(value: float) -> float:
    """Round estimates to honest display precision rather than false decimals."""
    magnitude = abs(value)
    if magnitude >= 100_000:
        step = 1_000.0
    elif magnitude >= 10_000:
        step = 100.0
    elif magnitude >= 1_000:
        step = 10.0
    elif magnitude >= 100:
        step = 1.0
    else:
        step = 0.1
    return round(value / step) * step


def confidence_label(score: int) -> str:
    if score >= 85:
        return "Very High"
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def _unavailable(reason: str, count: int = 0, span: float = 0.0) -> Estimate:
    return Estimate(
        EstimateStatus.UNAVAILABLE,
        UsageUnit.UNKNOWN,
        None,
        None,
        None,
        None,
        None,
        0,
        "Low",
        count,
        span,
        None,
        None,
        None,
        reason,
    )


def estimate_quota(
    samples: Iterable[Sample],
    *,
    now: datetime | None = None,
    stale_after_seconds: float = 12 * 60,
) -> Estimate:
    now = now or datetime.now(timezone.utc)
    candidates = sorted(samples, key=lambda sample: sample.timestamp)
    candidates = [
        sample
        for sample in candidates
        if sample.cumulative_usage is not None
        and math.isfinite(float(sample.cumulative_usage))
        and math.isfinite(sample.used_percent)
        and 0.0 <= sample.used_percent <= 100.0
        and not sample.stale
    ]
    if not candidates:
        return _unavailable("Cumulative usage is unavailable")

    units = {sample.usage_unit for sample in candidates}
    providers = {sample.provider for sample in candidates}
    signatures = {sample.source_signature for sample in candidates}
    limits = {sample.limit_id for sample in candidates}
    if len(units) != 1 or UsageUnit.UNKNOWN in units:
        return _unavailable("Samples use incompatible or unknown units", len(candidates))
    if len(providers) != 1 or len(signatures) != 1 or len(limits) != 1:
        return _unavailable("Provider, source, or limit identity changed", len(candidates))
    unit = next(iter(units))

    # Collapse exact duplicate observations while preserving chronological order.
    unique: list[Sample] = []
    seen: set[tuple[datetime, float, float]] = set()
    for sample in candidates:
        key = (sample.timestamp, sample.used_percent, float(sample.cumulative_usage))
        if key not in seen:
            unique.append(sample)
            seen.add(key)
    candidates = unique
    percentages = [sample.used_percent for sample in candidates]
    span = max(percentages) - min(percentages)
    if span < MIN_PERCENT_SPAN:
        return Estimate(
            EstimateStatus.WARMING_UP,
            unit,
            None,
            None,
            None,
            None,
            None,
            0,
            "Low",
            len(candidates),
            span,
            None,
            None,
            None,
            "Calibrating: about 5 percentage points of valid usage span are required",
        )
    if len(candidates) < MIN_USEFUL_SAMPLES:
        return _unavailable(
            "At least three valid samples are required after reaching the minimum span",
            len(candidates),
            span,
        )

    slopes: list[float] = []
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            delta_percent = right.used_percent - left.used_percent
            if abs(delta_percent) <= 0.25:
                continue
            delta_usage = float(right.cumulative_usage) - float(left.cumulative_usage)
            slope = delta_usage / delta_percent
            if math.isfinite(slope):
                slopes.append(slope)
    if not slopes:
        return _unavailable("No valid percentage-to-usage intervals", len(candidates), span)

    slope = _median(slopes)
    if slope <= 0 or not math.isfinite(slope):
        return _unavailable("Robust fitted slope is not positive", len(candidates), span)
    intercepts = [
        float(sample.cumulative_usage) - slope * sample.used_percent
        for sample in candidates
    ]
    intercept = _median(intercepts)
    residuals = [
        float(sample.cumulative_usage) - (intercept + slope * sample.used_percent)
        for sample in candidates
    ]
    residual_mad = _mad(residuals, 0.0)

    total = 100.0 * slope
    current_percent = candidates[-1].used_percent
    used = total * current_percent / 100.0
    remaining = max(0.0, total - used)

    slope_mad = _mad(slopes, slope)
    lower_slope = max(0.0, _quantile(slopes, 0.10))
    upper_slope = max(lower_slope, _quantile(slopes, 0.90))
    rounding_allowance = abs(slope) * 0.5
    uncertainty_usage = 1.4826 * residual_mad + rounding_allowance
    lower_bound = max(0.0, 100.0 * lower_slope - uncertainty_usage)
    upper_bound = max(total, 100.0 * upper_slope + uncertainty_usage)

    usage_range = max(
        1.0,
        max(float(sample.cumulative_usage) for sample in candidates)
        - min(float(sample.cumulative_usage) for sample in candidates),
    )
    count_score = _clamp((len(candidates) - 2) / 8.0)
    span_score = _clamp(span / 40.0)
    absolute_residuals = [abs(value) for value in residuals]
    residual_tail = _quantile(absolute_residuals, 0.90) / usage_range
    residual_noise = max(1.4826 * residual_mad / usage_range, residual_tail)
    residual_score = 1.0 / (1.0 + 6.0 * residual_noise)
    slope_deviations = [abs(value - slope) for value in slopes]
    slope_tail = _quantile(slope_deviations, 0.90) / abs(slope)
    slope_noise = max(1.4826 * slope_mad / abs(slope), slope_tail)
    slope_score = 1.0 / (1.0 + 4.0 * slope_noise)
    completeness = sum(sample.cumulative_usage is not None for sample in candidates) / len(
        candidates
    )
    newest_age = max(0.0, (now - candidates[-1].timestamp).total_seconds())
    freshness = _clamp(1.0 - newest_age / stale_after_seconds)
    mean_delay = statistics.fmean(sample.delay_seconds for sample in candidates)
    latency = _clamp(1.0 - mean_delay / 300.0)
    models = {sample.model for sample in candidates if sample.model}
    stability = 1.0
    warnings: list[str] = []
    if not models:
        stability *= 0.92
        warnings.append("Model information is unavailable")
    elif len(models) > 1:
        stability *= 0.72
        warnings.append("Credit-to-quota conversion may be model-dependent")

    base = 100.0 * (
        0.18 * count_score
        + 0.22 * span_score
        + 0.20 * residual_score
        + 0.15 * slope_score
        + 0.10 * completeness
        + 0.08 * freshness
        + 0.07 * latency
    )
    score = int(round(_clamp(base * stability, 0.0, 100.0)))
    if len(candidates) < 4:
        score = min(score, 70)
    if span < 10:
        score = min(score, 60)
    if newest_age >= stale_after_seconds:
        score = min(score, 25)
        warnings.append("Latest sample is stale")

    return Estimate(
        EstimateStatus.READY,
        unit,
        _rounded(total),
        _rounded(used),
        _rounded(remaining),
        _rounded(lower_bound),
        _rounded(upper_bound),
        score,
        confidence_label(score),
        len(candidates),
        span,
        slope,
        intercept,
        residual_mad,
        warnings=tuple(warnings),
    )


def build_baseline(estimates: Iterable[Estimate]) -> HistoricalBaseline | None:
    ready = [
        estimate
        for estimate in estimates
        if estimate.status is EstimateStatus.READY and estimate.total is not None
    ]
    if len(ready) < 2 or len({estimate.unit for estimate in ready}) != 1:
        return None
    totals = [float(estimate.total) for estimate in ready]
    median_total = _median(totals)
    return HistoricalBaseline(
        ready[0].unit, median_total, 1.4826 * _mad(totals, median_total), len(ready)
    )


def detect_quota_change(
    baseline: HistoricalBaseline | None,
    current: Estimate,
    *,
    minimum_confidence: int = 75,
    minimum_relative_change: float = 0.10,
) -> QuotaChangeAlert | None:
    if (
        baseline is None
        or current.status is not EstimateStatus.READY
        or current.total is None
        or current.unit is not baseline.unit
        or current.confidence < minimum_confidence
    ):
        return None
    difference = current.total - baseline.median_total
    relative = difference / baseline.median_total if baseline.median_total else 0.0
    robust_threshold = max(2.0 * baseline.robust_spread, baseline.median_total * 0.02)
    if abs(relative) < minimum_relative_change or abs(difference) <= robust_threshold:
        return None
    return QuotaChangeAlert(
        baseline.median_total,
        current.total,
        relative * 100.0,
        f"Possible quota change detected: {baseline.median_total:g} → ~{current.total:g} ({relative:+.0%})",
    )
