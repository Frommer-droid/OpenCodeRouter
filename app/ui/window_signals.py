from __future__ import annotations


def connect_window_signals(window) -> None:
    window.refresh_button.clicked.connect(window.refresh_all)
    window.use_button.clicked.connect(lambda: window.run_for_selected("use"))
    window.test_button.clicked.connect(lambda: window.run_command("scan"))
    window.auto_button.clicked.connect(lambda: window.run_command("auto"))
    window.different_ip_button.clicked.connect(
        lambda: window.run_command("auto", different_ip=True)
    )
    window.nodes_table.itemSelectionChanged.connect(window.update_action_state)
    window.nodes_table.itemDoubleClicked.connect(lambda _item: window.run_for_selected("use"))
    window.nodes_table.horizontalHeader().sectionClicked.connect(
        window.on_table_header_clicked
    )
    window.scale_combo.currentIndexChanged.connect(window.on_scale_delta_changed)
