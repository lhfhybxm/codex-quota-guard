from __future__ import annotations

from typing import Callable

from .qt_runtime import prepare_windows_qt_runtime

prepare_windows_qt_runtime()

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..models import CollectionResult, EstimateStatus, WindowType
from .formatting import format_number


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
        self.last_error: str | None = None

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

    def start(self) -> bool:
        if not self.available():
            self.last_error = "Windows reported that no system tray is available"
            return False
        try:
            self.icon = QSystemTrayIcon(self.app_icon())
            menu = QMenu()
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
        if self.icon is None or result.snapshot is None:
            return
        snapshot = result.snapshot
        parts = ["Codex"]
        for kind, label in ((WindowType.FIVE_HOUR, "5h"), (WindowType.WEEKLY, "7d")):
            window = snapshot.windows.get(kind)
            parts.append(f"{label} {window.used_percent:.0f}%" if window else f"{label} —")
        weekly = result.estimates.get(WindowType.WEEKLY)
        if weekly and weekly.status is EstimateStatus.READY:
            parts.append(f"Weekly ~{format_number(weekly.total)} {weekly.unit.value}")
        self.icon.setToolTip(" · ".join(parts)[:127])

    def stop(self) -> None:
        if self.icon is not None:
            self.icon.hide()
            self.icon.deleteLater()
            self.icon = None
