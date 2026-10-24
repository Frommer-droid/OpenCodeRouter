from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.core.app_config import ROUTER_SCRIPT, SETTINGS_FILE
from app.core.settings_store import SettingsStore
from app.services.router_process import RouterProcess


class ApplicationCore(QObject):
    busy_changed = Signal(bool, str)
    progress = Signal(str)
    result_ready = Signal(str, object, str, int)

    def __init__(self, logger: logging.Logger, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.logger = logger
        self.settings_store = SettingsStore(SETTINGS_FILE)
        self.settings: dict[str, Any] = self.settings_store.load()
        self.router = RouterProcess(ROUTER_SCRIPT, self)
        self.router.started.connect(self._on_started)
        self.router.progress.connect(self._on_progress)
        self.router.completed.connect(self._on_completed)

    @property
    def is_busy(self) -> bool:
        return self.router.is_running

    def execute(
        self, command: str, node: str | None = None, different_ip: bool = False
    ) -> bool:
        self.logger.info(
            "Запуск команды %s; узел=%s; другой_ip=%s",
            command,
            node or "—",
            different_ip,
        )
        return self.router.run(command, node, different_ip)

    def save_settings(self) -> None:
        self.settings_store.save(self.settings)

    def _on_started(self, command: str) -> None:
        self.busy_changed.emit(True, command)

    def _on_progress(self, message: str) -> None:
        self.logger.info(message)
        self.progress.emit(message)

    def _on_completed(self, command: str, payload: object, error: str, code: int) -> None:
        if code == 0:
            self.logger.info("Команда %s завершена", command)
        else:
            self.logger.error("Команда %s завершена с кодом %s: %s", command, code, error)
        self.busy_changed.emit(False, command)
        self.result_ready.emit(command, payload, error, code)
