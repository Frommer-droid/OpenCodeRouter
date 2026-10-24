from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.services.ui_scale_service import (
    normalize_ui_scale_delta_percent,
    normalize_ui_scale_percent,
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "window_pos_x": None,
    "window_pos_y": None,
    "window_width": 1000,
    "window_height": 720,
    "maximized": False,
    "autostart_enabled": False,
    "start_minimized": False,
    "ui_scale_mode": "auto",
    "ui_scale_delta_percent": 0,
    "ui_scale_percent": 100,
}


class SettingsStore:
    def __init__(self, settings_file: Path) -> None:
        self.settings_file = settings_file

    def load(self) -> dict[str, Any]:
        settings = deepcopy(DEFAULT_SETTINGS)
        loaded: dict[str, Any] = {}
        try:
            if self.settings_file.exists():
                candidate = json.loads(self.settings_file.read_text(encoding="utf-8"))
                if isinstance(candidate, dict):
                    loaded = candidate
                    settings.update(candidate)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
        self._migrate(settings, loaded)
        return settings

    def save(self, settings: dict[str, Any]) -> None:
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.settings_file.with_suffix(self.settings_file.suffix + ".tmp")
        temp_file.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temp_file.replace(self.settings_file)

    @staticmethod
    def _migrate(settings: dict[str, Any], loaded: dict[str, Any]) -> None:
        settings["maximized"] = bool(settings.get("maximized", False))
        settings["autostart_enabled"] = bool(settings.get("autostart_enabled", False))
        settings["start_minimized"] = bool(settings.get("start_minimized", False))
        settings["ui_scale_mode"] = "auto"

        if "ui_scale_delta_percent" not in loaded and "ui_scale_percent" in loaded:
            settings["ui_scale_delta_percent"] = int(loaded["ui_scale_percent"]) - 100
        settings["ui_scale_delta_percent"] = normalize_ui_scale_delta_percent(
            settings.get("ui_scale_delta_percent", 0)
        )
        settings["ui_scale_percent"] = normalize_ui_scale_percent(
            settings.get("ui_scale_percent", 100)
        )

        for key, fallback in (("window_width", 1000), ("window_height", 720)):
            try:
                settings[key] = max(320, int(settings.get(key, fallback)))
            except (TypeError, ValueError):
                settings[key] = fallback
