from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

APP_NAME = "OpenCodeRouter"
REQUIRED_ROOT_FILES = (
    "VERSION",
    "LICENSE",
    "OpenCodeRouter.ps1",
    "Router.Core.psm1",
    "NamedPipeHttp.cs",
    "OpenCodeRouter.config.example.json",
    "README.md",
    "RELEASE_NOTES.md",
    "THIRD_PARTY_NOTICES.md",
    "SOURCE_CODE_ACCESS.md",
    "QT_PYSIDE6_COMPLIANCE.md",
)


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _qt_runtime(target: Path) -> dict[str, list[str]]:
    internal = target / "_internal"
    return {
        "dlls": sorted(path.relative_to(internal).as_posix() for path in internal.rglob("Qt*.dll")),
        "plugins": sorted(
            path.relative_to(internal).as_posix()
            for path in internal.rglob("plugins")
            if path.is_dir()
        ),
    }


def main() -> int:
    build_tools = Path(__file__).resolve().parent
    project_root = build_tools.parent
    build_root = Path(os.environ.get("OPENCODE_ROUTER_BUILD_ROOT", project_root.parent / "temp-dev" / project_root.name / "release"))
    source = build_root / "dist" / APP_NAME
    target = Path(os.environ.get("OPENCODE_ROUTER_BUNDLE_DIR", project_root / APP_NAME))
    audit = build_root / "BUILD_AUDIT.json"
    if not source.is_dir() or not audit.is_file():
        raise FileNotFoundError("Нет проверенной dist-сборки или BUILD_AUDIT.json")
    for filename in REQUIRED_ROOT_FILES:
        project_file = project_root / filename
        if not project_file.is_file():
            raise FileNotFoundError(f"В проекте отсутствует release-файл: {filename}")
        shutil.copy2(project_file, source / filename)
    bundled_assets = source / "assets"
    if bundled_assets.exists():
        shutil.rmtree(bundled_assets)
    shutil.copytree(project_root / "assets", bundled_assets)
    if target.exists():
        raise FileExistsError(
            f"Старая корневая сборка должна быть удалена pre-build шагом: {target}"
        )

    shutil.move(str(source), str(target))
    public_audit = json.loads(audit.read_text(encoding="utf-8"))
    public_audit.pop("collect_toc", None)
    public_audit.pop("trusted_roots", None)
    for runtime in public_audit["pyside_msvc_runtime"].values():
        runtime.pop("source", None)
    (target / audit.name).write_text(json.dumps(public_audit, indent=2), encoding="utf-8")
    version = (project_root / "VERSION").read_text(encoding="utf-8").strip()
    manifest = {
        "manifest_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "application": {"name": APP_NAME, "version": version},
        "build_environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "PyInstaller": _package_version("PyInstaller"),
            "PySide6": _package_version("PySide6"),
            "shiboken6": _package_version("shiboken6"),
        },
        "qt_runtime": _qt_runtime(target),
        "local_runtime_data_included": False,
    }
    (target / "RUNTIME_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Preserve build work, caches and COLLECT evidence for owner inspection.
    print(f"Release folder: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
