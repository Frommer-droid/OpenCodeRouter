from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import QEvent, QRect, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QMoveEvent, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QSystemTrayIcon,
    QTableWidgetItem,
)

from app.core.app_config import APP_NAME, APP_VERSION, COLORS
from app.core.application import ApplicationCore
from app.services.ui_scale_service import resolve_ui_scale_from_screen, scale_px
from app.ui.icons import load_icon
from app.ui.styles import apply_global_styles
from app.ui.table_sorting import sort_node_rows
from app.ui.tray import TrayController
from app.ui.window_shell import apply_shell_metrics, build_window_shell
from app.ui.window_signals import connect_window_signals

COMMAND_LABELS = {
    "list": "Получение списка узлов",
    "status": "Проверка текущего маршрута",
    "scan": "Проверка всех узлов",
    "use": "Переключение маршрута",
    "test": "Временная проверка узла",
    "auto": "Поиск лучшего маршрута",
}
ROUTE_MONITOR_INTERVAL_MS = 5 * 60 * 1000


class MainWindow(QMainWindow):
    def __init__(self, core: ApplicationCore, auto_start: bool = True) -> None:
        super().__init__()
        self.core = core
        self._is_ready = False
        self._status_after_list = False
        self._refresh_list_after_command = False
        self._active_screen = None
        self._screen_connections: list[tuple[Any, Any]] = []
        self._restored_geometry = False
        self._node_rows: list[dict[str, Any]] = []
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._is_quitting = False
        self._tray_hint_shown = False
        self._background_status_pending = False
        self._automatic_failover_pending = False
        self._automatic_failover_origin = ""

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(680, 500)
        build_window_shell(self)
        connect_window_signals(self)
        self._connect_core()

        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.timeout.connect(self.save_window_geometry)

        self._set_saved_scale_combo()
        self._restore_geometry()
        self.apply_ui_scale(allow_window_resize=not self._restored_geometry, reason="startup")
        if self.core.settings.get("maximized"):
            self.showMaximized()
        else:
            self.show()
        QApplication.processEvents()
        self._install_scale_hooks()
        self._create_tray_icon()
        self._create_route_monitor()
        self._is_ready = True
        self.update_action_state()
        self.append_log("Приложение запущено.")
        self.tray.notify(
            APP_NAME,
            "Приложение запущено. Автопроверка маршрута — каждые 5 минут.",
        )
        if auto_start:
            QTimer.singleShot(250, self.refresh_all)

    def _create_tray_icon(self) -> None:
        app = QApplication.instance()
        icon = self.windowIcon()
        if icon.isNull() and app is not None:
            icon = app.windowIcon()
        self.tray = TrayController(self, icon)
        self.tray_icon = self.tray.icon
        self.tray_menu = self.tray.menu
        self.show_action = self.tray.show_action
        self.quit_action = self.tray.quit_action

    def _create_route_monitor(self) -> None:
        self.route_monitor_timer = QTimer(self)
        self.route_monitor_timer.setInterval(ROUTE_MONITOR_INTERVAL_MS)
        self.route_monitor_timer.timeout.connect(self.check_current_route_in_background)
        self.route_monitor_timer.start()

    def show_window(self) -> None:
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def quit_application(self) -> bool:
        if self.core.is_busy:
            self.show_window()
            QMessageBox.information(
                self,
                "Операция выполняется",
                "Дождитесь завершения проверки — это нужно для безопасного возврата маршрута.",
            )
            return False
        self._is_quitting = True
        self.save_window_geometry()
        self.tray.hide()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()
        return True

    def _connect_core(self) -> None:
        self.core.busy_changed.connect(self.on_busy_changed)
        self.core.progress.connect(self.on_progress)
        self.core.result_ready.connect(self.on_result)

    def _set_saved_scale_combo(self) -> None:
        delta = self.core.settings["ui_scale_delta_percent"]
        index = self.scale_combo.findData(delta)
        self.scale_combo.blockSignals(True)
        self.scale_combo.setCurrentIndex(max(0, index))
        self.scale_combo.blockSignals(False)

    def append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"{timestamp}  {message}")

    def refresh_all(self) -> None:
        if self.core.is_busy:
            return
        self._status_after_list = True
        self.run_command("list")

    def run_for_selected(self, command: str) -> None:
        node = self.selected_node()
        if node:
            self.run_command(command, node=node)

    def run_command(
        self,
        command: str,
        node: str | None = None,
        different_ip: bool = False,
        *,
        background: bool = False,
    ) -> bool:
        if self.core.is_busy:
            return False
        label = COMMAND_LABELS.get(command, command)
        suffix = f": {node}" if node else ""
        if different_ip:
            suffix = ": требуется новый IPv4"
        if not background:
            self.append_log(label + suffix)
        self._refresh_list_after_command = command in {"use", "test", "auto"}
        started = self.core.execute(command, node, different_ip)
        if not started:
            self.append_log("Команда не запущена.")
        return started

    def check_current_route_in_background(self) -> None:
        if (
            self.core.is_busy
            or self._background_status_pending
            or self._automatic_failover_pending
        ):
            return
        self._background_status_pending = True
        if not self.run_command("status", background=True):
            self._background_status_pending = False

    def selected_node(self) -> str | None:
        rows = self.nodes_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.nodes_table.item(rows[0].row(), 0)
        return item.text() if item else None

    def update_action_state(self) -> None:
        idle = not self.core.is_busy
        self.use_button.setEnabled(bool(self.selected_node()) and idle)
        self.test_button.setEnabled(bool(self._node_rows) and idle)

    def on_busy_changed(self, busy: bool, command: str) -> None:
        self.busy_bar.setVisible(busy)
        self.operation_label.setText(COMMAND_LABELS.get(command, command) if busy else "Готово")
        for button in (
            self.test_button,
            self.auto_button,
            self.different_ip_button,
            self.refresh_button,
        ):
            button.setEnabled(not busy)
        self.nodes_table.setEnabled(not busy)
        self.update_action_state()

    def on_progress(self, message: str) -> None:
        self.operation_label.setText(message)
        self.append_log(message)

    def on_result(self, command: str, payload: object, error: str, code: int) -> None:
        if command == "status" and self._background_status_pending:
            self._background_status_pending = False
            self._handle_background_status(payload, error, code)
            return
        if command == "auto" and self._automatic_failover_pending:
            self._handle_automatic_failover_result(payload, error, code)
            return

        if code == 0:
            self.append_log(f"{COMMAND_LABELS.get(command, command)}: готово.")
        else:
            short_error = self._friendly_error(error, code)
            self.append_log(short_error)
            self.operation_label.setText("Ошибка")

        if command == "list" and isinstance(payload, list):
            self._populate_nodes(payload)
            if self._status_after_list:
                self._status_after_list = False
                QTimer.singleShot(0, lambda: self.run_command("status"))
                return
        elif command == "scan" and isinstance(payload, list):
            self._populate_nodes(payload)
        elif isinstance(payload, dict):
            self._show_measurement(payload, command)

        if self._refresh_list_after_command and command in {"use", "test", "auto"}:
            self._refresh_list_after_command = False
            QTimer.singleShot(0, lambda: self.run_command("list"))

    def _handle_background_status(
        self, payload: object, error: str, code: int
    ) -> None:
        if isinstance(payload, dict):
            self._show_measurement(payload, "status", log_result=False)
        if code == 0 and isinstance(payload, dict) and bool(payload.get("ok")):
            return
        if self._is_clash_unavailable(error):
            self.append_log(self._friendly_error(error, code))
            self.tray.notify(
                "OpenCode Router: Clash недоступен",
                "Нет связи с Clash Verge Rev. Автопереключение невозможно.",
                QSystemTrayIcon.MessageIcon.Critical,
            )
            return

        origin = ""
        if isinstance(payload, dict):
            origin = str(payload.get("node") or "")
        self._automatic_failover_origin = origin or self.current_node_label.text()
        self.append_log(
            f"Маршрут {self._automatic_failover_origin} перестал отвечать; "
            "запущен последовательный поиск."
        )
        self.tray.notify(
            "OpenCode Router: переключение",
            f"{self._automatic_failover_origin} не отвечает. "
            "Ищу следующую рабочую локацию по алфавиту.",
            QSystemTrayIcon.MessageIcon.Warning,
        )
        QTimer.singleShot(0, self._start_automatic_failover)

    def _start_automatic_failover(self) -> None:
        if self.core.is_busy:
            return
        self._automatic_failover_pending = True
        if not self.run_command("auto", different_ip=True, background=True):
            self._automatic_failover_pending = False
            self.tray.notify(
                "OpenCode Router: переключение не запущено",
                "Не удалось запустить поиск следующей рабочей локации.",
                QSystemTrayIcon.MessageIcon.Critical,
            )

    def _handle_automatic_failover_result(
        self, payload: object, error: str, code: int
    ) -> None:
        self._automatic_failover_pending = False
        self._refresh_list_after_command = False
        if code == 0 and isinstance(payload, dict) and bool(payload.get("ok")):
            self._show_measurement(payload, "auto")
            node = str(payload.get("node") or "новая локация")
            ip = str(payload.get("ip") or "IP не получен")
            latency = payload.get("latencyMs")
            latency_text = f"{latency} мс" if latency is not None else "без замера"
            self.tray.notify(
                "OpenCode Router: маршрут переключён",
                f"{node}; {ip}; {latency_text}.",
            )
        elif self._is_clash_unavailable(error):
            self.append_log(self._friendly_error(error, code))
            self.tray.notify(
                "OpenCode Router: Clash недоступен",
                "Связь с Clash потеряна во время переключения.",
                QSystemTrayIcon.MessageIcon.Critical,
            )
        else:
            self.append_log(self._friendly_error(error, code))
            self.tray.notify(
                "OpenCode Router: рабочий маршрут не найден",
                "Проверен полный цикл локаций, но подключиться не удалось.",
                QSystemTrayIcon.MessageIcon.Critical,
            )
        QTimer.singleShot(0, lambda: self.run_command("list"))

    @staticmethod
    def _is_clash_unavailable(error: str) -> bool:
        cleaned = " ".join(error.split()).casefold()
        return (
            "named pipe controller request failed" in cleaned
            or "clash" in cleaned and "controller" in cleaned
        )

    @staticmethod
    def _friendly_error(error: str, code: int) -> str:
        cleaned = " ".join(error.split())
        if code == 2:
            return "Маршрут проверен, но не прошёл сетевую проверку."
        if "Another router command" in cleaned:
            return "Уже выполняется другая команда маршрутизатора."
        if "Named pipe controller request failed" in cleaned:
            return "Нет связи с Clash. Проверьте, что Clash Verge Rev запущен."
        return cleaned or "Не удалось выполнить команду."

    def _populate_nodes(self, rows: list[dict[str, Any]]) -> None:
        self._node_rows = [dict(row) for row in rows]
        self._render_node_rows()

    def on_table_header_clicked(self, column: int) -> None:
        selected_node = self.selected_node()
        if column == self._sort_column:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder
        self.nodes_table.horizontalHeader().setSortIndicator(
            self._sort_column, self._sort_order
        )
        self._render_node_rows(selected_node)

    def _render_node_rows(self, preferred_node: str | None = None) -> None:
        rows = sort_node_rows(
            self._node_rows,
            self._sort_column,
            descending=self._sort_order == Qt.SortOrder.DescendingOrder,
        )
        self.nodes_table.blockSignals(True)
        self.nodes_table.setUpdatesEnabled(False)
        self.nodes_table.clearContents()
        self.nodes_table.setRowCount(len(rows))
        selected_row = -1
        preferred_row = -1
        selected_data: dict[str, Any] | None = None
        for row_index, data in enumerate(rows):
            selected = bool(data.get("Selected"))
            if selected:
                selected_row = row_index
                selected_data = data
            if preferred_node and str(data.get("Node", "")) == preferred_node:
                preferred_row = row_index
            values = [
                str(data.get("Node", "")),
                str(data.get("IP") or "—"),
                str(data.get("API") or "не проверен"),
                f"{data['LatencyMs']} мс" if data.get("LatencyMs") is not None else "—",
                self._format_timestamp(str(data.get("CheckedUtc") or "")),
            ]
            failed = str(data.get("API") or "").upper() == "FAIL"
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if failed:
                    item.setBackground(QColor(COLORS["danger_surface"]))
                    if column == 2:
                        item.setForeground(QColor(COLORS["danger_text"]))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                if selected and column == 0:
                    item.setForeground(QColor(COLORS["success"]))
                    item.setIcon(load_icon("current"))
                    item.setToolTip("Текущий маршрут")
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.nodes_table.setItem(row_index, column, item)
        row_to_select = preferred_row if preferred_row >= 0 else selected_row
        if row_to_select >= 0:
            self.nodes_table.selectRow(row_to_select)
        self.nodes_table.setUpdatesEnabled(True)
        self.nodes_table.blockSignals(False)
        if selected_data is not None:
            self.current_node_label.setText(str(selected_data.get("Node", "—")))
            self.ip_label.setText(str(selected_data.get("IP") or "—"))
            latency = selected_data.get("LatencyMs")
            self.latency_label.setText(f"{latency} мс" if latency is not None else "—")
            api = str(selected_data.get("API", "untested"))
            if api == "OK":
                self._set_health(True)
            elif api == "FAIL":
                self._set_health(False)
            else:
                self._set_health(None)
        self.update_action_state()

    def _show_measurement(
        self, result: dict[str, Any], command: str, *, log_result: bool = True
    ) -> None:
        if command != "test":
            self.current_node_label.setText(str(result.get("node") or "—"))
        self.ip_label.setText(str(result.get("ip") or "—"))
        latency = result.get("latencyMs")
        self.latency_label.setText(f"{latency} мс" if latency is not None else "—")
        self._set_health(bool(result.get("ok")))
        node = result.get("node", "узел")
        ip = result.get("ip") or "IP не получен"
        state = "доступен" if result.get("ok") else "не прошёл проверку"
        restarted = result.get("connectionsRestarted")
        reconnect_text = (
            f"; переподключено соединений OpenCode: {restarted}"
            if restarted is not None
            else ""
        )
        if log_result:
            self.append_log(
                f"{node}: {state}; {ip}; {latency} мс{reconnect_text}."
            )

    def _set_health(self, healthy: bool | None) -> None:
        if healthy is True:
            text, object_name = "РАБОТАЕТ", "healthGood"
        elif healthy is False:
            text, object_name = "НЕДОСТУПЕН", "healthBad"
        else:
            text, object_name = "НЕ ПРОВЕРЕН", "healthUnknown"
        self.health_label.setText(text)
        self.health_label.setObjectName(object_name)
        self.health_label.style().unpolish(self.health_label)
        self.health_label.style().polish(self.health_label)

    @staticmethod
    def _format_timestamp(value: str) -> str:
        if not value:
            return "—"
        return value.replace("T", " ")[:19]

    def on_scale_delta_changed(self) -> None:
        if not self._is_ready:
            return
        self.core.settings["ui_scale_delta_percent"] = self.scale_combo.currentData()
        self.apply_ui_scale(allow_window_resize=True, reason="manual-delta")

    def apply_ui_scale(self, allow_window_resize: bool, reason: str) -> None:
        app = QApplication.instance()
        screen = self.screen() or (app.primaryScreen() if app else None)
        if app is None or screen is None:
            return
        state = resolve_ui_scale_from_screen(
            screen, self.core.settings.get("ui_scale_delta_percent", 0)
        )
        self.core.settings["ui_scale_mode"] = "auto"
        self.core.settings["ui_scale_delta_percent"] = state.delta_percent
        self.core.settings["ui_scale_percent"] = state.final_percent
        apply_global_styles(app, COLORS, state.scale_factor)
        apply_shell_metrics(self, state.scale_factor)
        self.scale_info_label.setText(
            f"Авто {state.auto_percent}% · итог {state.final_percent}%"
        )
        self.setMinimumSize(scale_px(680, state.scale_factor), scale_px(500, state.scale_factor))
        if allow_window_resize and not self.isMaximized():
            area = screen.availableGeometry()
            width = min(round(1000 * state.scale_factor), round(area.width() * 0.92))
            height = min(round(720 * state.scale_factor), round(area.height() * 0.9))
            self.resize(max(self.minimumWidth(), width), max(self.minimumHeight(), height))
        self.core.save_settings()
        if reason == "manual-delta":
            self.append_log(f"Масштаб интерфейса: {state.final_percent}%.")

    def _install_scale_hooks(self) -> None:
        handle = self.windowHandle()
        if handle is not None:
            handle.screenChanged.connect(self._on_screen_changed)
        app = QApplication.instance()
        if app is not None:
            app.primaryScreenChanged.connect(self._on_screen_topology_changed)
            app.screenAdded.connect(self._on_screen_topology_changed)
            app.screenRemoved.connect(self._on_screen_topology_changed)
        self._connect_active_screen(self.screen())

    def _connect_active_screen(self, screen) -> None:
        for signal, slot in self._screen_connections:
            try:
                signal.disconnect(slot)
            except RuntimeError:
                pass
        self._screen_connections.clear()
        self._active_screen = screen
        if screen is None:
            return
        for signal in (
            screen.logicalDotsPerInchChanged,
            screen.geometryChanged,
            screen.availableGeometryChanged,
        ):
            signal.connect(self._on_screen_metrics_changed)
            self._screen_connections.append((signal, self._on_screen_metrics_changed))

    def _on_screen_changed(self, screen) -> None:
        self._connect_active_screen(screen)
        self.apply_ui_scale(False, "screen-changed")

    def _on_screen_metrics_changed(self, *_args) -> None:
        self.apply_ui_scale(False, "screen-metrics")

    def _on_screen_topology_changed(self, *_args) -> None:
        self.apply_ui_scale(False, "screen-topology")

    def _restore_geometry(self) -> None:
        settings = self.core.settings
        x, y = settings.get("window_pos_x"), settings.get("window_pos_y")
        try:
            width = int(settings.get("window_width", 1000))
            height = int(settings.get("window_height", 720))
            position = (int(x), int(y)) if x is not None and y is not None else None
        except (TypeError, ValueError):
            width, height, position = 1000, 720, None
        if position is not None:
            proposed = QRect(position[0], position[1], width, height)
            app = QApplication.instance()
            if app and any(screen.availableGeometry().intersects(proposed) for screen in app.screens()):
                self.setGeometry(proposed)
                self._restored_geometry = True
        if not self._restored_geometry:
            self.resize(width, height)
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                area = screen.availableGeometry()
                self.move(area.center() - self.rect().center())
    def save_window_geometry(self) -> None:
        if not self._is_ready:
            return
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        self.core.settings.update(
            {
                "window_pos_x": geometry.x(),
                "window_pos_y": geometry.y(),
                "window_width": geometry.width(),
                "window_height": geometry.height(),
                "maximized": self.isMaximized(),
            }
        )
        self.core.save_settings()

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        if self._is_ready:
            self._geometry_timer.start(250)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._is_ready:
            self._geometry_timer.start(250)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self._is_ready:
            self._geometry_timer.start(250)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_quitting:
            self.save_window_geometry()
            event.accept()
            return
        self.save_window_geometry()
        event.ignore()
        self.hide()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.notify_window_hidden()
