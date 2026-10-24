from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.app_config import APP_NAME
from app.services.ui_scale_service import scale_px
from app.ui.icons import load_icon


def _metric(label: str, object_name: str) -> tuple[QWidget, QLabel]:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    caption = QLabel(label)
    caption.setObjectName("muted")
    value = QLabel("—")
    value.setObjectName(object_name)
    value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(caption)
    layout.addWidget(value)
    return box, value


def build_window_shell(window: QWidget) -> None:
    central = QWidget(window)
    window.setCentralWidget(central)  # type: ignore[attr-defined]
    window.root_layout = QVBoxLayout(central)

    header = QHBoxLayout()
    window.app_mark_label = QLabel()
    window.app_mark_label.setObjectName("appMark")
    window.app_mark_label.setAccessibleName("")
    window.app_mark_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    header.addWidget(window.app_mark_label, 0, Qt.AlignmentFlag.AlignTop)
    titles = QVBoxLayout()
    window.title_label = QLabel(APP_NAME)
    window.title_label.setObjectName("title")
    subtitle = QLabel("Отдельный IP для новых подключений OpenCode")
    subtitle.setObjectName("subtitle")
    titles.addWidget(window.title_label)
    titles.addWidget(subtitle)
    header.addLayout(titles, 1)

    scale_box = QVBoxLayout()
    scale_caption = QLabel("Масштаб интерфейса")
    scale_caption.setObjectName("muted")
    window.scale_combo = QComboBox()
    window.scale_combo.setAccessibleName("Масштаб интерфейса")
    for delta in range(-50, 51, 10):
        window.scale_combo.addItem(f"{100 + delta}%", delta)
    scale_box.addWidget(scale_caption)
    scale_box.addWidget(window.scale_combo)
    header.addLayout(scale_box)
    window.root_layout.addLayout(header)

    status_card = QFrame()
    status_card.setObjectName("card")
    window.status_layout = QGridLayout(status_card)
    node_box, window.current_node_label = _metric("Текущий маршрут", "metricValue")
    ip_box, window.ip_label = _metric("Внешний IPv4", "metricValue")
    latency_box, window.latency_label = _metric("Проверка", "metricValue")
    window.health_label = QLabel("НЕ ПРОВЕРЕН")
    window.health_label.setObjectName("healthUnknown")
    window.health_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.health_label.setAccessibleName("Состояние маршрута")
    window.status_layout.addWidget(node_box, 0, 0)
    window.status_layout.addWidget(ip_box, 0, 1)
    window.status_layout.addWidget(latency_box, 0, 2)
    window.status_layout.addWidget(window.health_label, 0, 3)
    window.root_layout.addWidget(status_card)

    table_header = QHBoxLayout()
    section = QLabel("Доступные узлы")
    section.setObjectName("sectionTitle")
    window.scale_info_label = QLabel()
    window.scale_info_label.setObjectName("scaleInfo")
    table_header.addWidget(section)
    table_header.addStretch(1)
    table_header.addWidget(window.scale_info_label)
    window.root_layout.addLayout(table_header)

    window.nodes_table = QTableWidget(0, 5)
    window.nodes_table.setHorizontalHeaderLabels(
        ["Узел", "IP", "API", "Задержка", "Проверен"]
    )
    window.nodes_table.setAlternatingRowColors(True)
    window.nodes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    window.nodes_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    window.nodes_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    window.nodes_table.setSortingEnabled(False)
    window.nodes_table.verticalHeader().setVisible(False)
    header_view = window.nodes_table.horizontalHeader()
    header_view.setSectionsClickable(True)
    header_view.setSortIndicatorShown(True)
    header_view.setSortIndicator(window._sort_column, window._sort_order)  # type: ignore[attr-defined]
    header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for column in (1, 2, 3, 4):
        header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
    window.nodes_table.setAccessibleName("Список VPN-узлов")
    window.nodes_table.setAccessibleDescription(
        "Нажмите заголовок столбца, чтобы изменить порядок сортировки"
    )
    for column in range(window.nodes_table.columnCount()):
        window.nodes_table.horizontalHeaderItem(column).setToolTip(
            "Нажмите для сортировки"
        )

    log_panel = QWidget()
    log_layout = QVBoxLayout(log_panel)
    log_layout.setContentsMargins(0, 0, 0, 0)
    log_title = QLabel("Ход выполнения")
    log_title.setObjectName("sectionTitle")
    window.log_view = QPlainTextEdit()
    window.log_view.setReadOnly(True)
    window.log_view.setMaximumBlockCount(500)
    window.log_view.setAccessibleName("Журнал выполнения")
    log_layout.addWidget(log_title)
    log_layout.addWidget(window.log_view)

    window.splitter = QSplitter(Qt.Orientation.Vertical)
    window.splitter.addWidget(window.nodes_table)
    window.splitter.addWidget(log_panel)
    window.splitter.setStretchFactor(0, 4)
    window.splitter.setStretchFactor(1, 1)
    window.root_layout.addWidget(window.splitter, 1)

    actions = QHBoxLayout()
    window.use_button = QPushButton("Переключить")
    window.use_button.setObjectName("primaryButton")
    window.use_button.setIcon(load_icon("switch"))
    window.use_button.setToolTip("Выбрать отмеченный узел и проверить его")
    window.test_button = QPushButton("Все узлы")
    window.test_button.setIcon(load_icon("test"))
    window.test_button.setAccessibleName("Проверить все узлы")
    window.test_button.setToolTip(
        "Проверить доступность и задержку всех узлов, не меняя текущий маршрут"
    )
    window.auto_button = QPushButton("Автовыбор")
    window.auto_button.setIcon(load_icon("auto"))
    window.auto_button.setToolTip("Проверить узлы и выбрать лучший рабочий")
    window.different_ip_button = QPushButton("Другой IP")
    window.different_ip_button.setIcon(load_icon("different_ip"))
    window.different_ip_button.setToolTip(
        "Найти следующий по алфавиту рабочий маршрут с другим IPv4"
    )
    window.refresh_button = QPushButton("Обновить")
    window.refresh_button.setIcon(load_icon("refresh"))
    window.refresh_button.setShortcut("F5")
    for button in (
        window.use_button,
        window.test_button,
        window.auto_button,
        window.different_ip_button,
        window.refresh_button,
    ):
        actions.addWidget(button)
    window.root_layout.addLayout(actions)

    footer = QHBoxLayout()
    window.busy_bar = QProgressBar()
    window.busy_bar.setRange(0, 0)
    window.busy_bar.setTextVisible(False)
    window.busy_bar.hide()
    window.operation_label = QLabel("Готово")
    window.operation_label.setObjectName("muted")
    footer.addWidget(window.busy_bar, 1)
    footer.addWidget(window.operation_label)
    window.root_layout.addLayout(footer)


def apply_shell_metrics(window: QWidget, scale_factor: float) -> None:
    def px(value: int | float) -> int:
        return scale_px(value, scale_factor)
    window.root_layout.setContentsMargins(px(22), px(20), px(22), px(18))
    window.root_layout.setSpacing(px(14))
    window.status_layout.setContentsMargins(px(18), px(15), px(18), px(15))
    window.status_layout.setHorizontalSpacing(px(24))
    window.status_layout.setVerticalSpacing(px(8))
    window.scale_combo.setMinimumWidth(px(112))
    mark_size = px(40)
    window.app_mark_label.setFixedSize(mark_size, mark_size)
    window.app_mark_label.setPixmap(
        load_icon("app").pixmap(QSize(mark_size, mark_size))
    )
    window.nodes_table.verticalHeader().setDefaultSectionSize(px(35))
    window.nodes_table.setIconSize(QSize(px(17), px(17)))
    window.log_view.setMinimumHeight(px(105))
    for button in (
        window.use_button,
        window.test_button,
        window.auto_button,
        window.different_ip_button,
        window.refresh_button,
    ):
        button.setMinimumHeight(px(40))
        button.setIconSize(QSize(px(18), px(18)))
