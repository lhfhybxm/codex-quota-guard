from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from codex_quota_guard.ui.qt_runtime import prepare_windows_qt_runtime

prepare_windows_qt_runtime()

from PySide6.QtWidgets import QApplication

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
from codex_quota_guard.storage import QuotaDatabase
from codex_quota_guard.ui.dashboard import Dashboard


def _result() -> CollectionResult:
    now = datetime.now(timezone.utc)
    weekly_window = WindowSnapshot(
        window_type=WindowType.WEEKLY,
        used_percent=27.5,
        resets_at=now + timedelta(days=4),
        duration_minutes=10_080,
        limit_id="weekly-test",
    )
    estimate = Estimate(
        status=EstimateStatus.WARMING_UP,
        unit=UsageUnit.TOKENS,
        total=None,
        used=None,
        remaining=None,
        lower_bound=None,
        upper_bound=None,
        confidence=0,
        confidence_label="warming",
        sample_count=3,
        percent_span=2.5,
        slope_per_percent=None,
        intercept=None,
        residual_mad=None,
        reason="More percentage movement is required",
    )
    health = ProviderHealth(
        provider="Codex App Server",
        last_success=now,
        status=Freshness.LIVE,
    )
    snapshot = QuotaSnapshot(
        timestamp=now,
        provider="Codex App Server",
        windows={WindowType.WEEKLY: weekly_window},
        account_usage=AccountUsage(supported=True, lifetime_tokens=123_456),
        plan_type="test",
    )
    return CollectionResult(snapshot=snapshot, estimates={WindowType.WEEKLY: estimate}, health=health)


def test_qml_dashboard_loads_and_reflects_provider_state(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    database = QuotaDatabase(tmp_path / "quota.db")
    dashboard = Dashboard(database, lambda: None, app.quit)
    try:
        assert dashboard.engine.rootObjects()
        dashboard.update(_result())
        assert dashboard.backend.freshness == "Live"
        assert dashboard.backend.weekly["percentText"] == "27.5%"
        assert dashboard.backend.weekly["badge"] == "CALIBRATING"
        assert dashboard.backend.fiveHour["badge"] == "UNAVAILABLE"
        assert "123,456" in dashboard.backend.usageSummary
    finally:
        dashboard.hide()
        database.close()
