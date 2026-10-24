import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.app_config import APP_ICON, COLORS
from app.core.settings_store import DEFAULT_SETTINGS
from app.ui.main_window import MainWindow
from app.ui.styles import build_global_stylesheet
from app.ui.tray import TrayController


class FakeCore(QObject):
    busy_changed = Signal(bool, str)
    progress = Signal(str)
    result_ready = Signal(str, object, str, int)

    def __init__(self) -> None:
        super().__init__()
        self.settings = DEFAULT_SETTINGS.copy()
        self.saved = 0
        self.busy = False
        self.execute_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    @property
    def is_busy(self) -> bool:
        return self.busy

    def execute(self, *args, **kwargs) -> bool:
        self.execute_calls.append((args, kwargs))
        return True

    def save_settings(self) -> None:
        self.saved += 1


def test_main_window_has_scale_control_and_actions() -> None:
    app = QApplication.instance() or QApplication([])
    core = FakeCore()
    window = MainWindow(core, auto_start=False)
    try:
        assert window.scale_combo.count() == 11
        assert window.scale_combo.itemData(0) == -50
        assert window.scale_combo.itemData(10) == 50
        assert window.use_button.text() == "Переключить"
        assert window.test_button.text() == "Все узлы"
        assert window.test_button.accessibleName() == "Проверить все узлы"
        assert not window.use_button.icon().isNull()
        assert not window.test_button.icon().isNull()
        assert not window.auto_button.icon().isNull()
        assert not window.different_ip_button.icon().isNull()
        assert not window.refresh_button.icon().isNull()
        assert window.app_mark_label.pixmap() is not None
        app_icon = QIcon(str(APP_ICON))
        assert not app_icon.isNull()
        assert QSize(16, 16) in app_icon.availableSizes()
        assert QSize(256, 256) in app_icon.availableSizes()
        assert window.nodes_table.columnCount() == 5
        assert window.route_monitor_timer.isActive()
        assert window.route_monitor_timer.interval() == 5 * 60 * 1000
        assert [
            window.nodes_table.horizontalHeaderItem(column).text()
            for column in range(window.nodes_table.columnCount())
        ] == ["Узел", "IP", "API", "Задержка", "Проверен"]
        window._populate_nodes(
            [
                {
                    "Selected": True,
                    "Node": "Нидерланды",
                    "IP": "203.0.113.4",
                    "API": "OK",
                    "LatencyMs": 125,
                    "CheckedUtc": "2026-09-08T18:00:00Z",
                },
                {
                    "Selected": False,
                    "Node": "Недоступный",
                    "IP": None,
                    "API": "FAIL",
                    "LatencyMs": 8000,
                    "CheckedUtc": "2026-09-08T18:01:00Z",
                },
            ]
        )
        assert window.current_node_label.text() == "Нидерланды"
        assert window.health_label.text() == "РАБОТАЕТ"
        assert window.use_button.isEnabled()
        assert window.test_button.isEnabled()
        window.test_button.click()
        assert core.execute_calls[-1][0] == ("scan", None, False)
        current_row = next(
            row for row in range(window.nodes_table.rowCount())
            if window.nodes_table.item(row, 0).text() == "Нидерланды"
        )
        failed_row = next(
            row for row in range(window.nodes_table.rowCount())
            if window.nodes_table.item(row, 0).text() == "Недоступный"
        )
        assert (
            window.nodes_table.item(current_row, 0).foreground().color().name().upper()
            == COLORS["success"]
        )
        assert not window.nodes_table.item(current_row, 0).icon().isNull()
        assert window.nodes_table.item(current_row, 0).toolTip() == "Текущий маршрут"
        for column in range(window.nodes_table.columnCount()):
            assert (
                window.nodes_table.item(failed_row, column).background().color().name().upper()
                == COLORS["danger_surface"]
            )
        assert (
            window.nodes_table.item(failed_row, 2).foreground().color().name().upper()
            == COLORS["danger_text"]
        )
        assert "font-size" in build_global_stylesheet(COLORS, 1.2)
        app.processEvents()
    finally:
        window._is_quitting = True
        window.close()


def test_stylesheet_is_applied_before_first_show(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet("")
    style_present_when_shown: list[bool] = []

    def record_show(_window) -> None:
        style_present_when_shown.append(bool(app.styleSheet()))

    monkeypatch.setattr(MainWindow, "show", record_show)
    window = MainWindow(FakeCore(), auto_start=False)
    try:
        assert style_present_when_shown == [True]
    finally:
        window._is_quitting = True
        window.close()


def test_close_hides_window_and_tray_restores_it() -> None:
    app = QApplication.instance() or QApplication([])
    core = FakeCore()
    window = MainWindow(core, auto_start=False)
    try:
        assert window.tray_icon.isVisible()
        assert [action.text() for action in window.tray_menu.actions()] == [
            "Показать",
            "",
            "Выход",
        ]

        window.close()
        app.processEvents()
        assert not window.isVisible()
        assert window.tray_icon.isVisible()

        window.show_action.trigger()
        app.processEvents()
        assert window.isVisible()
    finally:
        window._is_quitting = True
        window.close()


def test_tray_exit_is_refused_while_route_operation_is_busy(monkeypatch) -> None:
    QApplication.instance() or QApplication([])
    core = FakeCore()
    core.busy = True
    window = MainWindow(core, auto_start=False)
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda _parent, title, body: messages.append((title, body)),
    )
    try:
        assert window.quit_application() is False
        assert not window._is_quitting
        assert messages[0][0] == "Операция выполняется"

        window.close()
        assert not window.isVisible()
    finally:
        core.busy = False
        window._is_quitting = True
        window.close()


def test_tray_exit_marks_real_application_shutdown() -> None:
    QApplication.instance() or QApplication([])
    window = MainWindow(FakeCore(), auto_start=False)
    assert window.quit_application() is True
    assert window._is_quitting
    assert not window.tray_icon.isVisible()


def test_background_monitor_is_silent_for_a_healthy_route() -> None:
    QApplication.instance() or QApplication([])
    core = FakeCore()
    window = MainWindow(core, auto_start=False)
    notifications: list[tuple[str, str, object]] = []
    window.tray.notify = lambda title, body, icon=None: notifications.append(
        (title, body, icon)
    )
    try:
        window.check_current_route_in_background()
        assert core.execute_calls[-1][0] == ("status", None, False)

        window.on_result(
            "status",
            {
                "node": "Австрия",
                "ip": "203.0.113.10",
                "ok": True,
                "latencyMs": 210,
            },
            "",
            0,
        )

        assert notifications == []
        assert not window._background_status_pending
        assert not window._automatic_failover_pending
    finally:
        window._is_quitting = True
        window.close()


def test_background_monitor_switches_sequentially_after_route_failure() -> None:
    app = QApplication.instance() or QApplication([])
    core = FakeCore()
    window = MainWindow(core, auto_start=False)
    notifications: list[tuple[str, str, object]] = []
    window.tray.notify = lambda title, body, icon=None: notifications.append(
        (title, body, icon)
    )
    try:
        window.check_current_route_in_background()
        window.on_result(
            "status",
            {
                "node": "Австрия",
                "ip": None,
                "ok": False,
                "latencyMs": 8000,
            },
            "",
            2,
        )
        app.processEvents()

        assert core.execute_calls[-1][0] == ("auto", None, True)
        assert "Австрия" in notifications[-1][1]

        window.on_result(
            "auto",
            {
                "node": "Германия",
                "ip": "203.0.113.20",
                "ok": True,
                "latencyMs": 320,
            },
            "",
            0,
        )

        assert "Германия" in notifications[-1][1]
        assert "203.0.113.20" in notifications[-1][1]
        assert "320 мс" in notifications[-1][1]
        assert not window._automatic_failover_pending
    finally:
        window._is_quitting = True
        window.close()


def test_background_monitor_reports_clash_failure_without_failover() -> None:
    QApplication.instance() or QApplication([])
    core = FakeCore()
    window = MainWindow(core, auto_start=False)
    notifications: list[tuple[str, str, object]] = []
    window.tray.notify = lambda title, body, icon=None: notifications.append(
        (title, body, icon)
    )
    try:
        window.check_current_route_in_background()
        window.on_result(
            "status",
            None,
            "Named pipe controller request failed",
            1,
        )

        assert "Clash" in notifications[-1][1]
        assert len(core.execute_calls) == 1
        assert not window._automatic_failover_pending
    finally:
        window._is_quitting = True
        window.close()


def test_startup_is_reported_through_the_windows_tray(monkeypatch) -> None:
    QApplication.instance() or QApplication([])
    notifications: list[tuple[str, str]] = []

    def record_notification(
        _tray: TrayController, title: str, message: str, icon=None
    ) -> None:
        notifications.append((title, message))

    monkeypatch.setattr(TrayController, "notify", record_notification)
    window = MainWindow(FakeCore(), auto_start=False)
    try:
        assert notifications
        assert "запущено" in notifications[0][1]
        assert "5 минут" in notifications[0][1]
    finally:
        window._is_quitting = True
        window.close()
