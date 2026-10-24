from __future__ import annotations

from functools import lru_cache

from PySide6.QtGui import QIcon

from app.core.app_config import APP_MARK_ICON, APP_UI_ICON_DIR

ICON_FILES = {
    "app": APP_MARK_ICON,
    "switch": APP_UI_ICON_DIR / "switch.svg",
    "test": APP_UI_ICON_DIR / "test.svg",
    "auto": APP_UI_ICON_DIR / "auto.svg",
    "different_ip": APP_UI_ICON_DIR / "different-ip.svg",
    "refresh": APP_UI_ICON_DIR / "refresh.svg",
    "current": APP_UI_ICON_DIR / "current.svg",
    "show": APP_UI_ICON_DIR / "show.svg",
    "quit": APP_UI_ICON_DIR / "quit.svg",
}


@lru_cache(maxsize=None)
def load_icon(name: str) -> QIcon:
    try:
        path = ICON_FILES[name]
    except KeyError as exc:
        raise ValueError(f"Неизвестная иконка интерфейса: {name}") from exc
    return QIcon(str(path))
