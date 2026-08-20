from __future__ import annotations

from datetime import datetime, timedelta, timezone

from codex_quota_guard.models import (
    AccountUsage,
    CollectionResult,
    Estimate,
    EstimateStatus,
    Freshness,
    ProviderHealth,
    QuotaSnapshot,
    UsageUnit,
    WindowSnapshot,
    WindowType,
)
from codex_quota_guard.ui.qt_runtime import prepare_windows_qt_runtime

prepare_windows_qt_runtime()

from codex_quota_guard.ui.tray import build_tray_presentation


def _window(kind: WindowType, used: float, reset: datetime) -> WindowSnapshot:
    return WindowSnapshot(
        window_type=kind,
        used_percent=used,
        resets_at=reset,
        duration_minutes=300 if kind is WindowType.FIVE_HOUR else 10_080,
        limit_id=f"test-{kind.value}",
    )


def _result(*, include_weekly: bool = True, five_used: float = 63.7) -> CollectionResult:
    now = datetime(2026, 8, 20, 10, 30, tzinfo=timezone.utc)
    windows = {
        WindowType.FIVE_HOUR: _window(
            WindowType.FIVE_HOUR, five_used, now + timedelta(hours=2)
        )
    }
    estimates = {}
    if include_weekly:
        windows[WindowType.WEEKLY] = _window(
            WindowType.WEEKLY, 25.2, now + timedelta(days=4)
        )
        estimates[WindowType.WEEKLY] = Estimate(
            EstimateStatus.READY,
            UsageUnit.TOKENS,
            2_000_000,
            504_000,
            1_496_000,
            1_900_000,
            2_100_000,
            88,
            "Very High",
            12,
            22.0,
            20_000,
            0,
            100,
        )
    snapshot = QuotaSnapshot(
        timestamp=now,
        provider="Codex App Server",
        windows=windows,
        account_usage=AccountUsage(supported=True, lifetime_tokens=100_000),
    )
    health = ProviderHealth(
        provider="Codex App Server",
        last_success=now,
        status=Freshness.LIVE,
    )
    return CollectionResult(snapshot, estimates=estimates, health=health)


def test_tray_icon_prefers_weekly_remaining_and_hover_has_both_windows() -> None:
    presentation = build_tray_presentation(_result())

    assert presentation.icon_text == "75"
    assert "%" not in presentation.icon_text
    assert presentation.icon_basis == "Weekly"
    assert "7d 74.8 left / 25.2 used" in presentation.tooltip
    assert "5h 36.3 left / 63.7 used" in presentation.tooltip
    assert "Weekly estimated remaining: 1.5M tokens" in presentation.estimate_detail
    assert presentation.accent == "#51d88a"


def test_tray_icon_falls_back_to_five_hour_and_zero_pads_single_digit() -> None:
    presentation = build_tray_presentation(
        _result(include_weekly=False, five_used=96.4)
    )

    assert presentation.icon_text == "04"
    assert presentation.icon_basis == "5-hour"
    assert presentation.weekly_detail == "Weekly: unavailable"


def test_tray_unavailable_does_not_invent_a_percentage() -> None:
    health = ProviderHealth(
        provider="Codex App Server",
        status=Freshness.UNAVAILABLE,
    )
    presentation = build_tray_presentation(
        CollectionResult(None, health=health, error="[WinError 5] access denied")
    )

    assert presentation.icon_text == "--"
    assert presentation.icon_basis == "No live window"
    assert "access denied" in presentation.tooltip
    assert presentation.accent == "#ff6b72"
