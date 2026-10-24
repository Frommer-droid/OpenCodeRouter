from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_version_is_synchronized() -> None:
    version = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert version == "0.3.4"
    assert pyproject["project"]["version"] == version
    assert f"Версия {version}" in (PROJECT_ROOT / "RELEASE_NOTES.md").read_text(
        encoding="utf-8"
    )


def test_bundle_uses_public_config_template_only() -> None:
    spec_text = (PROJECT_ROOT / "Build_Tools" / "OpenCodeRouter.spec").read_text(
        encoding="utf-8"
    )
    assert '"OpenCodeRouter.config.example.json"' in spec_text
    assert '"OpenCodeRouter.config.json"' not in spec_text
    example = (PROJECT_ROOT / "OpenCodeRouter.config.example.json").read_text(
        encoding="utf-8"
    )
    assert '"secret": ""' in example
    assert "%APPDATA%" in example
    assert json.loads(example)["excludedNodes"] == []


def test_installer_contract_has_checked_run_and_complete_uninstall() -> None:
    module = _load_module(
        "build_installer",
        PROJECT_ROOT / "Build_Tools" / "build_installer.py",
    )
    text = module.iss_text(Path("C:/release"), Path("C:/output"), "0.3.1")
    run_line = next(
        line
        for line in text.splitlines()
        if line.startswith("Filename:") and "postinstall" in line
    )
    assert "nowait postinstall skipifsilent" in run_line
    assert "unchecked" not in run_line
    assert "UsePreviousAppDir=no" in text
    assert "Permissions: users-modify" in text
    assert "Type: filesandordirs" in text


def test_build_environment_does_not_inherit_machine_path(monkeypatch) -> None:
    module = _load_module(
        "build_release",
        PROJECT_ROOT / "Build_Tools" / "build_release.py",
    )
    monkeypatch.setenv("PATH", r"C:\ForeignToolchain")
    env = module.minimal_build_environment(PROJECT_ROOT)
    assert "ForeignToolchain" not in env["PATH"]
    assert str(PROJECT_ROOT / ".venv" / "Scripts") in env["PATH"]


def test_binary_origins_are_checked_before_runtime_replacement() -> None:
    text = (PROJECT_ROOT / "Build_Tools" / "OpenCodeRouter.spec").read_text(
        encoding="utf-8"
    )
    policy_calls = text[text.index("a = Analysis(") :]
    assert policy_calls.index("validate_trusted_binary_origins(") < policy_calls.index(
        "a.binaries = prefer_pyside_msvc_runtime("
    )


def test_installer_selects_drive_on_target_machine(monkeypatch) -> None:
    module = _load_module("installer_settings", PROJECT_ROOT / "Build_Tools" / "build_installer.py")
    monkeypatch.setenv("SystemDrive", "C:")
    monkeypatch.setattr(module, "local_build_settings", lambda: {})
    assert module.default_install_dir() == "{code:GetDefaultDir}"
    monkeypatch.setattr(module, "local_build_settings", lambda: {"installDir": "C:/Custom/Router"})
    text = module.iss_text(Path("C:/release"), Path("C:/output"), "0.3.2")
    assert "if DirExists('D:\\') then" in text
    assert "Result := 'D:\\Apps\\OpenCodeRouter'" in text
    assert "Result := 'C:\\Apps\\OpenCodeRouter'" in text
    assert "C:/Custom/Router" not in text
    assert "LanguageDetectionMethod=none" in text
    assert "ShowLanguageDialog=no" in text


def test_installer_honors_explicit_compiler(monkeypatch, tmp_path) -> None:
    module = _load_module("installer_compiler", PROJECT_ROOT / "Build_Tools" / "build_installer.py")
    compiler = tmp_path / "ISCC.exe"
    compiler.touch()
    monkeypatch.setenv("INNO_SETUP_ISCC", str(compiler))
    assert module.find_iscc() == compiler
