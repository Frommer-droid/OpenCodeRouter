from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from app.core.app_config import APP_NAME, APP_VERSION
from app.ui.icons import load_icon


class TrayController(QObject):
    """Own the notification-area icon and its user actions."""

    def __init__(self, window: QWidget, icon: QIcon) -> None:
        super().__init__(window)
        self.window = window
        self.menu = QMenu(window)

        self.show_action = QAction(load_icon("show"), "Показать", self.menu)
        self.show_action.triggered.connect(window.show_window)  # type: ignore[attr-defined]
        self.menu.addAction(self.show_action)
        self.menu.addSeparator()

        self.quit_action = QAction(load_icon("quit"), "Выход", self.menu)
        self.quit_action.triggered.connect(window.quit_application)  # type: ignore[attr-defined]
        self.menu.addAction(self.quit_action)

        self.icon = QSystemTrayIcon(icon, window)
        self.icon.setToolTip(f"{APP_NAME} {APP_VERSION}")
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._on_activated)
        self.icon.messageClicked.connect(window.show_window)  # type: ignore[attr-defined]
        self.icon.show()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.window.show_window()  # type: ignore[attr-defined]

    def notify_window_hidden(self) -> None:
        self.notify(
            APP_NAME,
            "Приложение продолжает работать в системном лотке.",
        )

    def notify(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon | None = None,
    ) -> None:
        """Show a Windows notification when the shell supports tray messages."""
        if not (
            QSystemTrayIcon.isSystemTrayAvailable()
            and QSystemTrayIcon.supportsMessages()
        ):
            return
        self.icon.showMessage(
            title,
            message,
            icon or QSystemTrayIcon.MessageIcon.Information,
            5000,
        )

    def hide(self) -> None:
        self.icon.hide()
