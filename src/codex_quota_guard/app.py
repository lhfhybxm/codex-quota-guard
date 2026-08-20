from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path

from .collector import SnapshotCollector
from .models import CollectionResult, EstimateStatus, WindowType
from .providers import CodexAppServerProvider
from .redaction import redact
from .storage import QuotaDatabase
from .ui.dashboard import Dashboard
from .ui.tray import TrayController


LOGGER = logging.getLogger(__name__)


def default_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "CodexQuotaGuard"
    return Path.home() / ".codex-quota-guard"


def configure_logging(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(data_dir / "app.log", encoding="utf-8")],
    )


def safe_result_dict(result: CollectionResult) -> dict[str, object]:
    snapshot = result.snapshot
    windows: dict[str, object] = {}
    if snapshot:
        for kind, window in snapshot.windows.items():
            estimate = result.estimates.get(kind)
            windows[kind.value] = {
                "usedPercent": window.used_percent,
                "resetsAt": window.resets_at.isoformat() if window.resets_at else None,
                "windowDurationMins": window.duration_minutes,
                "estimateStatus": estimate.status.value if estimate else None,
                "estimatedTotal": estimate.total if estimate else None,
                "estimatedRemaining": estimate.remaining if estimate else None,
                "unit": estimate.unit.value if estimate else None,
                "confidence": estimate.confidence if estimate else None,
            }
    return {
        "source": snapshot.provider if snapshot else "Codex App Server",
        "lastUpdated": (
            result.health.last_success.isoformat()
            if result.health and result.health.last_success
            else None
        ),
        "status": result.health.status.value if result.health else "unavailable",
        "inferenceOperationsInvoked": False,
        "windows": windows,
        "accountUsageSupported": snapshot.account_usage.supported if snapshot else None,
        "error": redact(result.error) if result.error else None,
    }


def run_once(data_dir: Path) -> int:
    configure_logging(data_dir)
    database = QuotaDatabase(data_dir / "quota.db")
    provider = CodexAppServerProvider()
    collector = SnapshotCollector(provider, database)
    try:
        result = collector.refresh(force=True)
        print(json.dumps(safe_result_dict(result), ensure_ascii=False, indent=2))
        return 0 if result.snapshot is not None else 1
    finally:
        collector.stop()
        database.close()


def run_gui(
    data_dir: Path, *, use_tray: bool = True, start_hidden: bool = False
) -> int:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication

    configure_logging(data_dir)
    database = QuotaDatabase(data_dir / "quota.db")
    provider = CodexAppServerProvider()
    collector = SnapshotCollector(provider, database)
    QQuickStyle.setStyle("Basic")
    application = QApplication.instance() or QApplication([sys.argv[0]])
    application.setApplicationName("Codex Quota Guard")
    application.setOrganizationName("Codex Quota Guard contributors")
    application.setWindowIcon(TrayController.app_icon())
    application.setQuitOnLastWindowClosed(False)
    shutting_down = threading.Event()

    def async_refresh() -> None:
        threading.Thread(
            target=lambda: collector.refresh(force=True),
            name="manual-quota-refresh",
            daemon=True,
        ).start()

    def close_application() -> None:
        if shutting_down.is_set():
            return
        shutting_down.set()
        tray.stop()
        collector.stop()
        database.close()
        application.quit()

    dashboard = Dashboard(
        database,
        refresh_callback=async_refresh,
        close_callback=close_application,
    )
    tray = TrayController(
        show_callback=dashboard.show,
        refresh_callback=async_refresh,
        exit_callback=close_application,
    )
    tray_started = use_tray and tray.start()
    dashboard.set_tray_status(tray_started, tray.last_error)
    if tray_started and start_hidden:
        dashboard.hide()
    else:
        dashboard.show()

    class ResultRelay(QObject):
        ready = Signal(object)

    relay = ResultRelay()

    def on_result(result: CollectionResult) -> None:
        if shutting_down.is_set():
            return
        dashboard.update(result)
        tray.update(result)

    relay.ready.connect(on_result)
    collector.add_listener(relay.ready.emit)
    collector_thread = threading.Thread(
        target=collector.run, name="quota-collector", daemon=True
    )
    collector_thread.start()
    try:
        return int(application.exec())
    except Exception as exc:
        LOGGER.error("GUI stopped: %s", redact(exc))
        return 1
    finally:
        if not shutting_down.is_set():
            shutting_down.set()
            tray.stop()
            collector.stop()
            database.close()
