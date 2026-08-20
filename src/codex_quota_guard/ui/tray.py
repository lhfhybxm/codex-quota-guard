from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .qt_runtime import prepare_windows_qt_runtime

prepare_windows_qt_runtime()

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..models import (
    CollectionResult,
    EstimateStatus,
    Freshness,
    WindowSnapshot,
    WindowType,
)
from ..redaction import redact
from .formatting import UNIT_LABELS, format_compact_number


@dataclass(frozen=True, slots=True)
class TrayPresentation:
    icon_text: str
    icon_basis: str
    accent: str
    tooltip: str
    weekly_detail: str
    five_hour_detail: str
    estimate_detail: str
    source_detail: str


def _remaining(window: WindowSnapshot) -> float:
    return max(0.0, min(100.0, 100.0 - window.used_percent))


def _reset_text(window: WindowSnapshot, *, weekly: bool) -> str:
    if window.resets_at is None:
        return "unknown reset"
    local = window.resets_at.astimezone()
    return local.strftime("%m-%d %H:%M") if weekly else local.strftime("%H:%M")


def _window_detail(window: WindowSnapshot | None, label: str, *, weekly: bool) -> str:
    if window is None:
        return f"{label}: unavailable"
    return (
        f"{label}: {_remaining(window):.1f}% remaining · "
        f"{window.used_percent:.1f}% used · reset {_reset_text(window, weekly=weekly)}"
    )


def _tooltip_window_line(window: WindowSnapshot | None, label: str, *, weekly: bool) -> str:
    if window is None:
        return f"{label} unavailable"
    return (
        f"{label} {_remaining(window):.1f} left / {window.used_percent:.1f} used / "
        f"{_reset_text(window, weekly=weekly)}"
    )


def _updated_text(value: datetime | None) -> str:
    return value.astimezone().strftime("%H:%M") if value else "never"


def build_tray_presentation(result: CollectionResult) -> TrayPresentation:
    snapshot = result.snapshot
    health = result.health
    weekly = snapshot.windows.get(WindowType.WEEKLY) if snapshot else None
    five_hour = snapshot.windows.get(WindowType.FIVE_HOUR) if snapshot else None
    preferred = weekly or five_hour
    icon_basis = "Weekly" if weekly else "5-hour" if five_hour else "No live window"
    if preferred is None:
        icon_text = "--"
    else:
        rounded = int(round(_remaining(preferred)))
        icon_text = str(rounded) if rounded == 100 else f"{rounded:02d}"

    freshness = health.status if health else Freshness.UNAVAILABLE
    accent = (
        "#51d88a"
        if freshness is Freshness.LIVE
        else "#f5b84b"
        if freshness is Freshness.STALE
        else "#ff6b72"
    )
    provider = (
        snapshot.provider
        if snapshot
        else health.provider
        if health
        else "Codex App Server"
    )
    last_success = health.last_success if health else None
    source_detail = (
        f"Source: {provider} · {freshness.value} · updated {_updated_text(last_success)}"
    )

    estimate = result.estimates.get(WindowType.WEEKLY)
    if (
        estimate
        and estimate.status is EstimateStatus.READY
        and estimate.remaining is not None
    ):
        estimate_detail = (
            f"Weekly estimated remaining: {format_compact_number(estimate.remaining)} "
            f"{UNIT_LABELS[estimate.unit]} · confidence {estimate.confidence}%"
        )
    elif estimate and estimate.status is EstimateStatus.WARMING_UP:
        estimate_detail = f"Weekly estimate: calibrating ({estimate.percent_span:.1f}% span)"
    else:
        estimate_detail = "Weekly absolute estimate: unavailable"

    tooltip_lines = [
        "Codex Quota Guard",
        _tooltip_window_line(weekly, "7d", weekly=True),
        _tooltip_window_line(five_hour, "5h", weekly=False),
        f"Updated {_updated_text(last_success)}",
    ]
    if snapshot is None and result.error:
        tooltip_lines[2] = redact(result.error)[:56]

    return TrayPresentation(
        icon_text=icon_text,
        icon_basis=icon_basis,
        accent=accent,
        tooltip="\n".join(tooltip_lines),
        weekly_detail=_window_detail(weekly, "Weekly", weekly=True),
        five_hour_detail=_window_detail(five_hour, "5-hour", weekly=False),
        estimate_detail=estimate_detail,
        source_detail=source_detail,
    )


class TrayController:
    def __init__(
        self,
        show_callback: Callable[[], None],
        refresh_callback: Callable[[], None],
        exit_callback: Callable[[], None],
    ) -> None:
        self.show_callback = show_callback
        self.refresh_callback = refresh_callback
        self.exit_callback = exit_callback
        self.icon: QSystemTrayIcon | None = None
        self.menu: QMenu | None = None
        self.last_error: str | None = None
        self.icon_basis_action: QAction | None = None
        self.weekly_action: QAction | None = None
        self.five_hour_action: QAction | None = None
        self.estimate_action: QAction | None = None
        self.source_action: QAction | None = None

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    @staticmethod
    def app_icon() -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#252a33"), 1))
        painter.setBrush(QColor("#12151a"))
        painter.drawRoundedRect(3, 3, 58, 58, 16, 16)
        painter.setBrush(QColor("transparent"))
        base_pen = QPen(QColor("#343a46"), 6)
        base_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(base_pen)
        painter.drawArc(15, 15, 34, 34, 35 * 16, 290 * 16)
        accent_pen = QPen(QColor("#8b8cff"), 6)
        accent_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(accent_pen)
        painter.drawArc(15, 15, 34, 34, 35 * 16, 205 * 16)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#51d88a"))
        painter.drawEllipse(43, 42, 8, 8)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def remaining_icon(text: str, accent: str) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#111419"))
        painter.setPen(QPen(QColor(accent), 3))
        painter.drawRoundedRect(3, 3, 58, 58, 15, 15)
        font = QFont("Segoe UI Variable Display")
        font.setBold(True)
        font.setPixelSize(25 if len(text) >= 3 else 32)
        painter.setFont(font)
        painter.setPen(QColor("#f7f8fa"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(accent))
        painter.drawEllipse(49, 49, 8, 8)
        painter.end()
        return QIcon(pixmap)

    def start(self) -> bool:
        if not self.available():
            self.last_error = "Windows reported that no system tray is available"
            return False
        try:
            self.icon = QSystemTrayIcon(self.remaining_icon("--", "#8f98a8"))
            menu = QMenu()
            self.menu = menu
            self.icon_basis_action = QAction(
                "Icon: waiting for an official window", menu
            )
            self.weekly_action = QAction("Weekly: waiting", menu)
            self.five_hour_action = QAction("5-hour: waiting", menu)
            self.estimate_action = QAction("Estimate: waiting", menu)
            self.source_action = QAction("Source: Codex App Server · starting", menu)
            for action in (
                self.icon_basis_action,
                self.weekly_action,
                self.five_hour_action,
                self.estimate_action,
                self.source_action,
            ):
                action.setEnabled(False)
                menu.addAction(action)
            menu.addSeparator()
            open_action = QAction("Open dashboard", menu)
            open_action.triggered.connect(self.show_callback)
            refresh_action = QAction("Refresh (read-only)", menu)
            refresh_action.triggered.connect(self.refresh_callback)
            exit_action = QAction("Exit", menu)
            exit_action.triggered.connect(self.exit_callback)
            menu.addAction(open_action)
            menu.addAction(refresh_action)
            menu.addSeparator()
            menu.addAction(exit_action)
            self.icon.setContextMenu(menu)
            self.icon.setToolTip("Codex Quota Guard · starting")
            self.icon.activated.connect(self._activated)
            self.icon.show()
            return self.icon.isVisible()
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.icon = None
            return False

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.show_callback()

    def update(self, result: CollectionResult) -> None:
        if self.icon is None:
            return
        presentation = build_tray_presentation(result)
        self.icon.setIcon(
            self.remaining_icon(presentation.icon_text, presentation.accent)
        )
        self.icon.setToolTip(presentation.tooltip)
        if self.icon_basis_action is not None:
            self.icon_basis_action.setText(
                f"Icon: {presentation.icon_basis} remaining {presentation.icon_text}"
            )
        if self.weekly_action is not None:
            self.weekly_action.setText(presentation.weekly_detail)
        if self.five_hour_action is not None:
            self.five_hour_action.setText(presentation.five_hour_detail)
        if self.estimate_action is not None:
            self.estimate_action.setText(presentation.estimate_detail)
        if self.source_action is not None:
            self.source_action.setText(presentation.source_detail)

    def stop(self) -> None:
        if self.icon is not None:
            self.icon.hide()
            self.icon.deleteLater()
            self.icon = None
        if self.menu is not None:
            self.menu.deleteLater()
            self.menu = None
