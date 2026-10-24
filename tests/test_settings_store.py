import json

from app.core.settings_store import SettingsStore


def test_defaults_are_returned_for_missing_file(tmp_path) -> None:
    settings = SettingsStore(tmp_path / "settings.json").load()
    assert settings["window_width"] == 1000
    assert settings["ui_scale_delta_percent"] == 0
    assert settings["ui_scale_mode"] == "auto"


def test_legacy_absolute_scale_is_migrated_to_delta(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"ui_scale_percent": 130}), encoding="utf-8")
    settings = SettingsStore(path).load()
    assert settings["ui_scale_delta_percent"] == 30


def test_save_is_atomic_and_keeps_unicode(tmp_path) -> None:
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.save({"node": "Нидерланды"})
    assert json.loads(path.read_text(encoding="utf-8"))["node"] == "Нидерланды"
    assert not path.with_suffix(".json.tmp").exists()
