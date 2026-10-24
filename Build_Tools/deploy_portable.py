from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

APP_NAME = "OpenCodeRouter"


def safe_target(parent: Path) -> Path:
    resolved_parent = parent.resolve()
    target = (resolved_parent / APP_NAME).resolve()
    if target == resolved_parent:
        raise RuntimeError("Целевая папка совпала с родительской")
    target.relative_to(resolved_parent)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    settings_path = Path(__file__).resolve().parents[1] / "private" / "build-settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    default_parent = settings.get("portableParent")
    parser.add_argument(
        "--destination-parent", type=Path, default=default_parent,
        required=not bool(default_parent),
    )
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent
    source = Path(os.environ.get("OPENCODE_ROUTER_BUNDLE_DIR", project_root / APP_NAME)).resolve()
    parent = args.destination_parent.resolve()
    target = safe_target(parent)
    if not source.is_dir() or not (source / f"{APP_NAME}.exe").is_file():
        raise FileNotFoundError(f"Нет готовой release-папки: {source}")
    parent.mkdir(parents=True, exist_ok=True)
    # Overlay product files without deleting user settings, logs or caches.
    shutil.copytree(source, target, dirs_exist_ok=True)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
