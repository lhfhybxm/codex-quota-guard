from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .qt_runtime import prepare_windows_qt_runtime

prepare_windows_qt_runtime()

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, Qt, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine

from ..estimator import build_baseline, detect_quota_change
from ..models import CollectionResult, Estimate, EstimateStatus, Freshness, UsageUnit, WindowType
from ..redaction import redact
from ..storage import QuotaDatabase
from .formatting import UNIT_LABELS, format_compact_number, format_number, format_reset


COLORS = {
    "accent": "#8b8cff",
    "green": "#51d88a",
    "amber": "#f5b84b",
    "red": "#ff6b72",
    "muted": "#8f98a8",
}


class HistoryModel(QAbstractListModel):
    WindowRole = Qt.ItemDataRole.UserRole + 1
    PeriodRole = Qt.ItemDataRole.UserRole + 2
    ObservedRole = Qt.ItemDataRole.UserRole + 3
    EstimateRole = Qt.ItemDataRole.UserRole + 4
    ConfidenceRole = Qt.ItemDataRole.UserRole + 5
    StatusRole = Qt.ItemDataRole.UserRole + 6

    def __init__(self, database: QuotaDatabase) -> None:
        super().__init__()
        self.database = database
        self._rows: list[dict[str, str]] = []
        self.refresh()

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802 - Qt API name
        return {
            self.WindowRole: b"windowName",
            self.PeriodRole: b"period",
            self.ObservedRole: b"observed",
            self.EstimateRole: b"estimate",
            self.ConfidenceRole: b"confidence",
            self.StatusRole: b"status",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        key = {
            self.WindowRole: "windowName",
            self.PeriodRole: "period",
            self.ObservedRole: "observed",
            self.EstimateRole: "estimate",
            self.ConfidenceRole: "confidence",
            self.StatusRole: "status",
        }.get(role)
        return self._rows[index.row()].get(key) if key else None

    @Slot()
    def refresh(self) -> None:
        rows: list[dict[str, str]] = []
        for item in self.database.epoch_summaries(limit=100):
            start = item.started_at.astimezone().strftime("%Y-%m-%d %H:%M")
            end = item.ended_at.astimezone().strftime("%m-%d %H:%M") if item.ended_at else "now"
            estimate = "—"
            if item.estimated_total is not None:
                estimate = f"~{format_number(item.estimated_total)} {UNIT_LABELS[item.unit]}"
            rows.append(
                {
                    "windowName": "5-hour" if item.window_type is WindowType.FIVE_HOUR else "Weekly",
                    "period": f"{start}  →  {end}",
                    "observed": f"{item.first_percent:.1f}%  →  {item.last_percent:.1f}%",
                    "estimate": estimate,
                    "confidence": f"{item.confidence}%" if item.confidence is not None else "—",
                    "status": "Complete" if item.completed else "Active",
                }
            )
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class DashboardBackend(QObject):
    dataChanged = Signal()
    refreshRequested = Signal()
    exitRequested = Signal()
    hideRequested = Signal()

    def __init__(self, history: HistoryModel) -> None:
        super().__init__()
        self.history = history
        self._freshness = "Waiting"
        self._freshness_color = COLORS["muted"]
        self._last_updated = "Waiting for the first read-only sample"
        self._provider = "Codex App Server"
        self._plan = "—"
        self._error = ""
        self._quota_alert = ""
        self._usage_summary = "Token telemetry has not been reported yet."
        self._tray_available = False
        self._tray_detail = "Tray is initializing"
        self._five_hour = self._empty_window(WindowType.FIVE_HOUR)
        self._weekly = self._empty_window(WindowType.WEEKLY)

    @staticmethod
    def _empty_window(kind: WindowType) -> dict[str, Any]:
        is_weekly = kind is WindowType.WEEKLY
        return {
            "title": "Weekly limit" if is_weekly else "5-hour limit",
            "subtitle": "Long-horizon allowance" if is_weekly else "Short rolling window",
            "available": False,
            "usedPercent": 0.0,
            "percentText": "—",
            "resetText": "No active window reported",
            "badge": "UNAVAILABLE",
            "badgeColor": COLORS["muted"],
            "total": "—",
            "totalLabel": "ESTIMATED TOTAL",
            "used": "—",
            "remaining": "—",
            "range": "Absolute quota unavailable",
            "confidence": "Waiting for provider data",
            "detail": "This window was not returned by the official read-only endpoint.",
            "sampleCount": "0 samples",
            "span": "0.0% observed span",
        }

    @Property(str, notify=dataChanged)
    def freshness(self) -> str:
        return self._freshness

    @Property(str, notify=dataChanged)
    def freshnessColor(self) -> str:  # noqa: N802
        return self._freshness_color

    @Property(str, notify=dataChanged)
    def lastUpdated(self) -> str:  # noqa: N802
        return self._last_updated

    @Property(str, notify=dataChanged)
    def provider(self) -> str:
        return self._provider

    @Property(str, notify=dataChanged)
    def plan(self) -> str:
        return self._plan

    @Property(str, notify=dataChanged)
    def error(self) -> str:
        return self._error

    @Property(str, notify=dataChanged)
    def quotaAlert(self) -> str:  # noqa: N802
        return self._quota_alert

    @Property(str, notify=dataChanged)
    def usageSummary(self) -> str:  # noqa: N802
        return self._usage_summary

    @Property("QVariantMap", notify=dataChanged)
    def fiveHour(self) -> dict[str, Any]:  # noqa: N802
        return self._five_hour

    @Property("QVariantMap", notify=dataChanged)
    def weekly(self) -> dict[str, Any]:
        return self._weekly

    @Property(bool, notify=dataChanged)
    def trayAvailable(self) -> bool:  # noqa: N802
        return self._tray_available

    @Property(str, notify=dataChanged)
    def trayDetail(self) -> str:  # noqa: N802
        return self._tray_detail

    @Slot()
    def requestRefresh(self) -> None:  # noqa: N802
        self.refreshRequested.emit()

    @Slot()
    def requestClose(self) -> None:  # noqa: N802
        if self._tray_available:
            self.hideRequested.emit()
        else:
            self.exitRequested.emit()

    def set_tray_status(self, available: bool, detail: str | None = None) -> None:
        self._tray_available = available
        self._tray_detail = detail or (
            "Available · closing the window keeps monitoring active"
            if available
            else "Unavailable · closing the window exits the app"
        )
        self.dataChanged.emit()

    def update_result(self, result: CollectionResult) -> None:
        snapshot = result.snapshot
        health = result.health
        freshness = health.status if health else Freshness.UNAVAILABLE
        if freshness is Freshness.LIVE:
            self._freshness, self._freshness_color = "Live", COLORS["green"]
        elif freshness is Freshness.STALE:
            self._freshness, self._freshness_color = "Delayed", COLORS["amber"]
        else:
            self._freshness, self._freshness_color = "Unavailable", COLORS["red"]

        if health and health.last_success:
            self._last_updated = f"Updated {health.last_success.astimezone().strftime('%H:%M:%S')}"
        else:
            self._last_updated = "No successful sample yet"
        self._provider = snapshot.provider if snapshot else (health.provider if health else "Codex App Server")
        self._plan = snapshot.plan_type or "—" if snapshot else "—"
        raw_error = result.error or (health.error if health else None)
        self._error = redact(raw_error) if raw_error else ""

        if snapshot and snapshot.account_usage.supported:
            lifetime = snapshot.account_usage.lifetime_tokens
            self._usage_summary = (
                f"Official lifetime usage: {format_number(lifetime)} tokens"
                if lifetime is not None
                else "Official usage endpoint is available; no lifetime total was returned."
            )
        elif snapshot and snapshot.account_usage.error:
            self._usage_summary = f"Token telemetry unavailable: {redact(snapshot.account_usage.error)}"
        else:
            self._usage_summary = "Token telemetry has not been reported yet."

        alerts: list[str] = []
        baselines = {}
        for kind in (WindowType.FIVE_HOUR, WindowType.WEEKLY):
            baseline = build_baseline(self.history.database.completed_estimates(kind))
            baselines[kind] = baseline
            estimate = result.estimates.get(kind)
            if estimate is not None:
                alert = detect_quota_change(baseline, estimate)
                if alert:
                    label = "5-hour" if kind is WindowType.FIVE_HOUR else "Weekly"
                    alerts.append(f"{label}: {alert.message}")
        self._quota_alert = "  ·  ".join(alerts)

        self._five_hour = self._window_map(result, WindowType.FIVE_HOUR, baselines[WindowType.FIVE_HOUR])
        self._weekly = self._window_map(result, WindowType.WEEKLY, baselines[WindowType.WEEKLY])
        self.history.refresh()
        self.dataChanged.emit()

    def _window_map(self, result: CollectionResult, kind: WindowType, baseline: Any) -> dict[str, Any]:
        value = self._empty_window(kind)
        snapshot = result.snapshot
        window = snapshot.windows.get(kind) if snapshot else None
        estimate = result.estimates.get(kind)
        if window is None:
            return value

        value.update(
            {
                "available": True,
                "usedPercent": max(0.0, min(100.0, window.used_percent)),
                "percentText": f"{window.used_percent:.1f}%",
                "resetText": f"Resets {format_reset(window.resets_at, kind is WindowType.WEEKLY)}",
            }
        )
        self._apply_estimate(value, estimate, baseline)
        return value

    @staticmethod
    def _apply_estimate(value: dict[str, Any], estimate: Estimate | None, baseline: Any) -> None:
        if estimate is None or estimate.status is EstimateStatus.UNAVAILABLE:
            value.update(
                {
                    "badge": "UNAVAILABLE",
                    "badgeColor": COLORS["muted"],
                    "range": "Absolute quota unavailable",
                    "confidence": estimate.reason if estimate and estimate.reason else "Waiting for usable token samples",
                    "detail": "Official percentage is shown without inventing an absolute allowance.",
                }
            )
            return
        if estimate.status is EstimateStatus.WARMING_UP:
            historical_total = "—"
            total_label = "ESTIMATED TOTAL"
            detail = estimate.reason or "Keep Codex running normally; the monitor never generates usage."
            if baseline is not None:
                historical_total = f"~{format_compact_number(baseline.median_total)} {UNIT_LABELS[baseline.unit]}"
                total_label = "HISTORICAL MEDIAN"
                detail = f"Historical baseline from {baseline.epoch_count} complete cycles; current cycle is still calibrating."
            value.update(
                {
                    "badge": "CALIBRATING",
                    "badgeColor": COLORS["amber"],
                    "range": "Collecting a reliable usage span",
                    "confidence": f"{estimate.percent_span:.1f}% of about 5% required",
                    "total": historical_total,
                    "totalLabel": total_label,
                    "detail": detail,
                    "sampleCount": f"{estimate.sample_count} samples",
                    "span": f"{estimate.percent_span:.1f}% observed span",
                }
            )
            return

        unit = UNIT_LABELS[estimate.unit]
        value.update(
            {
                "badge": "ESTIMATED",
                "badgeColor": COLORS["green"],
                "total": f"{format_compact_number(estimate.total)} {unit}",
                "used": f"{format_compact_number(estimate.used)} {unit}",
                "remaining": f"{format_compact_number(estimate.remaining)} {unit}",
                "range": f"Likely {format_number(estimate.lower_bound)}–{format_number(estimate.upper_bound)} {unit}",
                "confidence": f"Confidence {estimate.confidence}% · {estimate.confidence_label}",
                "detail": "Robust fit across this reset epoch; values remain estimates.",
                "sampleCount": f"{estimate.sample_count} samples",
                "span": f"{estimate.percent_span:.1f}% observed span",
            }
        )


class Dashboard:
    def __init__(
        self,
        database: QuotaDatabase,
        refresh_callback: Callable[[], None],
        close_callback: Callable[[], None],
    ) -> None:
        self.history = HistoryModel(database)
        self.backend = DashboardBackend(self.history)
        self.backend.refreshRequested.connect(refresh_callback)
        self.backend.exitRequested.connect(close_callback)
        self.backend.hideRequested.connect(self.hide)

        self.engine = QQmlApplicationEngine()
        context = self.engine.rootContext()
        context.setContextProperty("backend", self.backend)
        context.setContextProperty("historyModel", self.history)
        qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
        self.engine.load(qml_path)
        roots = self.engine.rootObjects()
        if not roots:
            raise RuntimeError(f"Unable to load dashboard QML: {qml_path}")
        self.window = roots[0]

    def set_tray_status(self, available: bool, detail: str | None = None) -> None:
        self.backend.set_tray_status(available, detail)

    def update(self, result: CollectionResult) -> None:
        self.backend.update_result(result)

    def show(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.requestActivate()

    def hide(self) -> None:
        self.window.hide()
