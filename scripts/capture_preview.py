from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

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
from codex_quota_guard.ui.qt_runtime import prepare_windows_qt_runtime

prepare_windows_qt_runtime()

from PySide6.QtCore import QTimer
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication


def demo_result() -> CollectionResult:
    now = datetime.now(timezone.utc)
    five_hour = WindowSnapshot(
        WindowType.FIVE_HOUR,
        42.8,
        now + timedelta(hours=2, minutes=14),
        300,
        "demo-five-hour",
    )
    weekly = WindowSnapshot(
        WindowType.WEEKLY,
        34.2,
        now + timedelta(days=4, hours=8),
        10_080,
        "demo-weekly",
    )
    five_estimate = Estimate(
        EstimateStatus.WARMING_UP,
        UsageUnit.TOKENS,
        None,
        None,
        None,
        None,
        None,
        0,
        "Low",
        7,
        4.1,
        None,
        None,
        None,
        "Calibrating: about 5 percentage points of valid usage span are required",
    )
    weekly_estimate = Estimate(
        EstimateStatus.READY,
        UsageUnit.TOKENS,
        2_480_000,
        848_000,
        1_632_000,
        2_400_000,
        2_570_000,
        86,
        "Very High",
        12,
        22.4,
        24_800,
        82_000_000,
        6_300,
    )
    snapshot = QuotaSnapshot(
        now,
        "Codex App Server",
        {WindowType.FIVE_HOUR: five_hour, WindowType.WEEKLY: weekly},
        AccountUsage(supported=True, lifetime_tokens=89_230_000),
        plan_type="Plus",
        source_version="demo",
    )
    health = ProviderHealth(
        provider="Codex App Server",
        last_success=now,
        status=Freshness.LIVE,
    )
    return CollectionResult(
        snapshot=snapshot,
        estimates={WindowType.FIVE_HOUR: five_estimate, WindowType.WEEKLY: weekly_estimate},
        health=health,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a deterministic README preview")
    parser.add_argument("output", type=Path)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing preview: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    QQuickStyle.setStyle("Basic")
    application = QApplication([])
    database = QuotaDatabase(args.database)
    dashboard = Dashboard(database, lambda: None, application.quit)
    dashboard.set_tray_status(True)
    dashboard.update(demo_result())
    dashboard.window.setWidth(1180)
    dashboard.window.setHeight(760)
    dashboard.show()
    result = {"ok": False}

    def capture() -> None:
        image = dashboard.window.grabWindow()
        result["ok"] = not image.isNull() and image.save(str(output), "PNG")
        application.quit()

    QTimer.singleShot(650, capture)
    application.exec()
    dashboard.hide()
    database.close()
    if not result["ok"]:
        raise RuntimeError("Qt Quick returned an empty preview image")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
