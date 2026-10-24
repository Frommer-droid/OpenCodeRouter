from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "OpenCode Router"
APP_USER_MODEL_ID = "frommer.opencoderouter.desktop.1"


def get_app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


APP_DIR = get_app_directory()
SETTINGS_FILE = APP_DIR / "settings.json"
LOG_FILE = APP_DIR / "logs" / "gui.log"
VERSION_FILE = APP_DIR / "VERSION"
ROUTER_SCRIPT = APP_DIR / "OpenCodeRouter.ps1"
APP_ICON = APP_DIR / "assets" / "router.ico"
APP_MARK_ICON = APP_DIR / "assets" / "router.svg"
APP_UI_ICON_DIR = APP_DIR / "assets" / "icons"


def read_app_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


APP_VERSION = read_app_version()

COLORS = {
    "background": "#282C34",
    "surface": "#21252B",
    "surface_alt": "#2C313C",
    "surface_hover": "#353B45",
    "surface_pressed": "#181A1F",
    "alternate": "#262A32",
    "selection": "#3E4451",
    "primary": "#3E4451",
    "primary_hover": "#4B5263",
    "accent": "#61AFEF",
    "accent_hover": "#7BC0F6",
    "accent_pressed": "#4D95C7",
    "success": "#98C379",
    "text": "#ABB2BF",
    "text_strong": "#E6E6E6",
    "muted": "#9DA5B4",
    "on_accent": "#21252B",
    "border": "#3E4451",
    "focus": "#61AFEF",
    "danger": "#E06C75",
    "danger_text": "#E8838B",
    "danger_surface": "#352A31",
    "warning": "#D19A66",
    "disabled_text": "#5C6370",
    "disabled_background": "#21252B",
    "disabled_border": "#2C313C",
    "scrollbar": "#4B5263",
}
