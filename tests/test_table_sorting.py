import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication

from app.core.settings_store import DEFAULT_SETTINGS
from app.ui.main_window import MainWindow
from app.ui.table_sorting import sort_node_rows


class FakeCore(QObject):
    busy_changed = Signal(bool, str)
    progress = Signal(str)
    result_ready = Signal(str, object, str, int)

    def __init__(self) -> None:
        super().__init__()
        self.settings = DEFAULT_SETTINGS.copy()

    @property
    def is_busy(self) -> bool:
        return False

    def execute(self, *_args, **_kwargs) -> bool:
        return True

    def save_settings(self) -> None:
        pass


ROWS = [
    {
        "Selected": False,
        "Node": "Медленный",
        "IP": "203.0.113.10",
        "API": "FAIL",
        "LatencyMs": 900,
        "CheckedUtc": "2026-09-08T19:00:00Z",
    },
    {
        "Selected": True,
        "Node": "Быстрый",
        "IP": "192.0.2.2",
        "API": "OK",
        "LatencyMs": 120,
        "CheckedUtc": "2026-09-08T20:00:00Z",
    },
    {
        "Selected": False,
        "Node": "Не проверен",
        "IP": None,
        "API": "untested",
        "LatencyMs": None,
        "CheckedUtc": None,
    },
]


def _node_order(window: MainWindow) -> list[str]:
    return [
        window.nodes_table.item(row, 0).text()
        for row in range(window.nodes_table.rowCount())
    ]


def test_node_table_sorts_numeric_and_keeps_unknown_values_last() -> None:
    _app = QApplication.instance() or QApplication([])
    window = MainWindow(FakeCore(), auto_start=False)
    try:
        window._populate_nodes(ROWS)
        assert _node_order(window) == ["Быстрый", "Медленный", "Не проверен"]

        window.nodes_table.horizontalHeader().sectionClicked.emit(3)
        assert _node_order(window) == ["Быстрый", "Медленный", "Не проверен"]

        window.nodes_table.horizontalHeader().sectionClicked.emit(3)
        assert _node_order(window) == ["Медленный", "Быстрый", "Не проверен"]

        window.nodes_table.horizontalHeader().sectionClicked.emit(1)
        assert _node_order(window) == ["Быстрый", "Медленный", "Не проверен"]

        window.nodes_table.horizontalHeader().sectionClicked.emit(2)
        assert _node_order(window) == ["Быстрый", "Медленный", "Не проверен"]
        assert window.nodes_table.horizontalHeader().sortIndicatorSection() == 2
    finally:
        window.close()


def test_startup_sort_uses_russian_node_names_instead_of_latency_or_flags() -> None:
    _app = QApplication.instance() or QApplication([])
    window = MainWindow(FakeCore(), auto_start=False)
    rows = [
        {"Node": "🇩🇪 Германия ⭐", "LatencyMs": 10, "Selected": True},
        {"Node": "🇬🇧 Великобритания 🚀", "LatencyMs": 50},
        {"Node": "🇦🇹 Австрия ⭐", "LatencyMs": 100},
    ]
    try:
        header = window.nodes_table.horizontalHeader()
        assert header.sortIndicatorSection() == 0
        assert header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
        window._populate_nodes(rows)
        assert _node_order(window) == [
            "🇦🇹 Австрия ⭐", "🇬🇧 Великобритания 🚀", "🇩🇪 Германия ⭐"
        ]
        window._populate_nodes(list(reversed(rows)))
        assert _node_order(window)[0] == "🇦🇹 Австрия ⭐"
        assert window.selected_node() == "🇩🇪 Германия ⭐"
    finally:
        window.close()


def test_sort_keys_cover_every_visible_column() -> None:
    assert [row["Node"] for row in sort_node_rows(ROWS, 0)] == [
        "Быстрый",
        "Медленный",
        "Не проверен",
    ]
    assert [row["Node"] for row in sort_node_rows(ROWS, 1, descending=True)] == [
        "Медленный",
        "Быстрый",
        "Не проверен",
    ]
    assert [row["Node"] for row in sort_node_rows(ROWS, 2, descending=True)] == [
        "Медленный",
        "Быстрый",
        "Не проверен",
    ]
    assert [row["Node"] for row in sort_node_rows(ROWS, 4, descending=True)] == [
        "Быстрый",
        "Медленный",
        "Не проверен",
    ]


def test_node_column_uses_russian_location_name_after_country_prefix() -> None:
    rows = [
        {"Node": "🇩🇪 Германия ⭐"},
        {"Node": "GB Великобритания ⭐"},
        {"Node": "🇦🇹 Австрия ⭐"},
    ]

    assert [row["Node"] for row in sort_node_rows(rows, 0)] == [
        "🇦🇹 Австрия ⭐",
        "GB Великобритания ⭐",
        "🇩🇪 Германия ⭐",
    ]
    assert [row["Node"] for row in sort_node_rows(rows, 0, descending=True)] == [
        "🇩🇪 Германия ⭐",
        "GB Великобритания ⭐",
        "🇦🇹 Австрия ⭐",
    ]
