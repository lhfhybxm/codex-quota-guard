from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from codex_quota_guard.estimator import (
    build_baseline,
    detect_quota_change,
    estimate_quota,
)
from codex_quota_guard.models import (
    Estimate,
    EstimateStatus,
    Sample,
    UsageUnit,
    WindowType,
)


NOW = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)


def sample(
    index: int,
    percent: float,
    usage: float | None,
    *,
    unit: UsageUnit = UsageUnit.CREDITS,
    model: str | None = "gpt-test",
    stale: bool = False,
) -> Sample:
    return Sample(
        WindowType.WEEKLY,
        NOW + timedelta(minutes=index),
        percent,
        NOW + timedelta(days=7),
        10080,
        usage,
        unit,
        "fixture",
        "codex",
        model=model,
        source_signature="fixture-v1",
        stale=stale,
    )


def ready(total: float, confidence: int = 90) -> Estimate:
    return Estimate(
        EstimateStatus.READY,
        UsageUnit.CREDITS,
        total,
        None,
        None,
        total * 0.98,
        total * 1.02,
        confidence,
        "High",
        10,
        40,
        total / 100,
        1000,
        1,
    )


def test_linear_growth_from_zero_uses_slope_not_intercept() -> None:
    points = [sample(i, p, 1_000 + 25 * p) for i, p in enumerate((0, 10, 20, 30))]
    estimate = estimate_quota(points, now=NOW + timedelta(minutes=4))
    assert estimate.status is EstimateStatus.READY
    assert estimate.total == pytest.approx(2_500)
    assert estimate.intercept == pytest.approx(1_000)


def test_installing_at_32_percent_still_estimates_total() -> None:
    points = [sample(i, p, 7_500 + 25 * p) for i, p in enumerate((32.1, 37.4, 45.0, 54.0))]
    assert estimate_quota(points, now=NOW + timedelta(minutes=5)).total == pytest.approx(2_500)


def test_percentage_rounding_remains_close() -> None:
    true_percentages = (9.7, 20.3, 30.4, 40.2, 50.1)
    points = [
        sample(i, round(p), 4_000 + 25 * p) for i, p in enumerate(true_percentages)
    ]
    estimate = estimate_quota(points, now=NOW + timedelta(minutes=6))
    assert estimate.total == pytest.approx(2_500, rel=0.04)
    assert estimate.lower_bound < estimate.upper_bound


def test_theil_sen_resists_one_usage_outlier() -> None:
    usage = [1_000, 1_250, 9_000, 1_750, 2_000, 2_250]
    points = [sample(i, p, value) for i, (p, value) in enumerate(zip(range(0, 60, 10), usage))]
    estimate = estimate_quota(points, now=NOW + timedelta(minutes=7))
    assert estimate.total == pytest.approx(2_500)
    assert estimate.confidence < 85


def test_span_below_five_percent_is_warming_up() -> None:
    points = [sample(i, p, 100 + 25 * p) for i, p in enumerate((32.0, 34.0, 36.0))]
    estimate = estimate_quota(points, now=NOW + timedelta(minutes=4))
    assert estimate.status is EstimateStatus.WARMING_UP
    assert estimate.total is None


def test_first_valid_sample_is_warming_up_not_unavailable() -> None:
    estimate = estimate_quota([sample(0, 32.0, 1_234)], now=NOW)
    assert estimate.status is EstimateStatus.WARMING_UP
    assert estimate.percent_span == 0


def test_missing_usage_and_cost_stay_missing() -> None:
    points = [sample(i, p, None) for i, p in enumerate((10, 20, 30))]
    assert all(point.cost_usd is None for point in points)
    assert estimate_quota(points, now=NOW).status is EstimateStatus.UNAVAILABLE


def test_stale_samples_do_not_create_false_estimate() -> None:
    points = [sample(i, p, 25 * p, stale=True) for i, p in enumerate((10, 20, 30))]
    assert estimate_quota(points, now=NOW).status is EstimateStatus.UNAVAILABLE


def test_model_mixture_reduces_confidence_and_warns() -> None:
    points = [
        sample(i, p, 1_000 + 25 * p, model="a" if i < 3 else "b")
        for i, p in enumerate((0, 10, 20, 30, 40, 50))
    ]
    estimate = estimate_quota(points, now=NOW + timedelta(minutes=7))
    assert estimate.status is EstimateStatus.READY
    assert estimate.confidence < 75
    assert any("model-dependent" in warning for warning in estimate.warnings)


def test_multiple_historical_cycles_form_baseline_and_detect_change() -> None:
    baseline = build_baseline([ready(2_490), ready(2_500), ready(2_510)])
    assert baseline is not None
    assert baseline.median_total == 2_500
    alert = detect_quota_change(baseline, ready(3_200, 91))
    assert alert is not None
    assert alert.percent_change == pytest.approx(28.0)
