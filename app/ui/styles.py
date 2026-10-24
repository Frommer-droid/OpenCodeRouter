from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.services.ui_scale_service import scale_point_size, scale_px


def build_global_stylesheet(
    colors: dict[str, str], scale_factor: float = 1.0, base_font_size: float = 10.0
) -> str:
    def px(value: int | float) -> int:
        return scale_px(value, scale_factor)

    def pt(value: int | float) -> float:
        return scale_point_size(value, scale_factor)
    return f"""
        QWidget {{
            background: {colors['background']};
            color: {colors['text']};
            font-family: "Segoe UI", "Aptos", sans-serif;
            font-size: {pt(base_font_size)}pt;
        }}
        QMainWindow {{ background: {colors['background']}; }}
        QFrame#card {{
            background: {colors['surface']};
            border: {px(1)}px solid {colors['border']};
            border-radius: {px(10)}px;
        }}
        QFrame#card QWidget {{ background: transparent; }}
        QLabel#title {{ color: {colors['text_strong']}; font-size: {pt(19)}pt; font-weight: 700; }}
        QLabel#subtitle, QLabel#muted, QLabel#scaleInfo {{ color: {colors['muted']}; }}
        QLabel#sectionTitle {{ color: {colors['text_strong']}; font-size: {pt(11)}pt; font-weight: 600; }}
        QLabel#metricValue {{ color: {colors['text_strong']}; font-size: {pt(15)}pt; font-weight: 650; }}
        QLabel#healthGood {{
            color: {colors['on_accent']};
            background: {colors['success']};
            border-radius: {px(10)}px;
            padding: {px(3)}px {px(9)}px;
            font-weight: 700;
        }}
        QLabel#healthBad {{
            color: {colors['on_accent']};
            background: {colors['danger']};
            border-radius: {px(10)}px;
            padding: {px(3)}px {px(9)}px;
            font-weight: 700;
        }}
        QLabel#healthUnknown {{
            color: {colors['text']};
            background: {colors['primary']};
            border-radius: {px(10)}px;
            padding: {px(3)}px {px(9)}px;
            font-weight: 600;
        }}
        QPushButton {{
            background: {colors['surface_alt']};
            border: {px(1)}px solid {colors['border']};
            border-radius: {px(7)}px;
            padding: {px(7)}px {px(13)}px;
            font-weight: 600;
        }}
        QPushButton:hover {{ border-color: {colors['focus']}; background: {colors['surface_hover']}; }}
        QPushButton:pressed {{ background: {colors['surface_pressed']}; }}
        QPushButton:focus {{ border: {px(2)}px solid {colors['focus']}; }}
        QPushButton:disabled {{
            color: {colors['disabled_text']};
            background: {colors['disabled_background']};
            border-color: {colors['disabled_border']};
        }}
        QPushButton#primaryButton {{
            color: {colors['on_accent']};
            background: {colors['accent']};
            border-color: {colors['accent']};
        }}
        QPushButton#primaryButton:hover {{ background: {colors['accent_hover']}; }}
        QPushButton#primaryButton:pressed {{ background: {colors['accent_pressed']}; }}
        QPushButton#primaryButton:disabled {{
            color: {colors['disabled_text']};
            background: {colors['disabled_background']};
            border-color: {colors['disabled_border']};
        }}
        QComboBox, QPlainTextEdit {{
            background: {colors['surface_alt']};
            border: {px(1)}px solid {colors['border']};
            border-radius: {px(6)}px;
            padding: {px(6)}px {px(8)}px;
            selection-background-color: {colors['selection']};
        }}
        QComboBox:focus, QPlainTextEdit:focus {{ border-color: {colors['focus']}; }}
        QComboBox::drop-down {{ border: 0; width: {px(24)}px; }}
        QTableWidget {{
            background: {colors['background']};
            alternate-background-color: {colors['alternate']};
            border: {px(1)}px solid {colors['border']};
            border-radius: {px(7)}px;
            gridline-color: {colors['border']};
            selection-background-color: {colors['selection']};
            selection-color: {colors['text_strong']};
        }}
        QHeaderView::section {{
            background: {colors['surface_alt']};
            color: {colors['muted']};
            border: 0;
            border-bottom: {px(1)}px solid {colors['border']};
            padding: {px(7)}px;
            font-weight: 600;
        }}
        QHeaderView::section:hover {{ background: {colors['surface_hover']}; }}
        QProgressBar {{
            border: 0;
            background: {colors['surface_alt']};
            border-radius: {px(2)}px;
            max-height: {px(4)}px;
        }}
        QProgressBar::chunk {{ background: {colors['accent']}; border-radius: {px(2)}px; }}
        QSplitter::handle {{ background: {colors['border']}; height: {px(1)}px; }}
        QScrollBar:vertical {{ width: {px(10)}px; background: transparent; }}
        QScrollBar::handle:vertical {{
            background: {colors['scrollbar']};
            border-radius: {px(4)}px;
            min-height: {px(24)}px;
        }}
        QToolTip {{
            color: {colors['text']};
            background: {colors['surface']};
            border: {px(1)}px solid {colors['focus']};
            padding: {px(4)}px;
        }}
    """


def apply_global_styles(
    app: QApplication, colors: dict[str, str], scale_factor: float = 1.0
) -> None:
    font = QFont(app.font())
    font.setFamilies(["Segoe UI", "Aptos"])
    app.setFont(font)
    app.setStyleSheet(
        build_global_stylesheet(colors, scale_factor, max(9.0, font.pointSizeF()))
    )
