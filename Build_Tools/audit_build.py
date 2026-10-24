from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import PySide6
from runtime_dll_policy import PYSIDE_MSVC_RUNTIME_NAMES

APP_NAME = "OpenCodeRouter"
BINARY_TYPES = {"BINARY", "EXTENSION", "EXECUTABLE"}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _binary_entries(value: Any):
    if isinstance(value, (list, tuple)):
        if len(value) >= 3 and value[2] in BINARY_TYPES:
            yield str(value[0]), Path(str(value[1])).resolve(), str(value[2])
        else:
            for item in value:
                yield from _binary_entries(item)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    build_tools = Path(__file__).resolve().parent
    project_root = build_tools.parent
    build_root = Path(os.environ.get("OPENCODE_ROUTER_BUILD_ROOT", project_root.parent / "temp-dev" / project_root.name / "release"))
    toc_path = build_root / "build" / APP_NAME / "COLLECT-00.toc"
    dist_root = build_root / "dist" / APP_NAME
    if not toc_path.is_file() or not dist_root.is_dir():
        raise FileNotFoundError("Для аудита нужны COLLECT-00.toc и готовая dist-папка")

    toc = ast.literal_eval(toc_path.read_text(encoding="utf-8"))
    entries = list(_binary_entries(toc))
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    trusted_roots = tuple(
        Path(path).resolve()
        for path in (project_root, Path(sys.prefix), Path(sys.base_prefix), system_root)
    )
    foreign = [
        {"destination": destination, "source": str(source), "type": typecode}
        for destination, source, typecode in entries
        if not any(_inside(source, root) for root in trusted_roots)
        and not (
            typecode == "EXECUTABLE"
            and destination == f"{APP_NAME}.exe"
            and source == (build_root / "build" / APP_NAME / f"{APP_NAME}.exe").resolve()
        )
    ]
    if foreign:
        raise RuntimeError(
            "COLLECT-00.toc содержит foreign binary origins:\n"
            + "\n".join(f"{item['destination']} <- {item['source']}" for item in foreign)
        )

    pyside_root = Path(PySide6.__file__).resolve().parent
    runtime: dict[str, dict[str, str]] = {}
    for filename in PYSIDE_MSVC_RUNTIME_NAMES:
        bundled = dist_root / "_internal" / filename
        source = pyside_root / filename
        if not bundled.is_file() or not source.is_file():
            raise FileNotFoundError(f"Не найден обязательный MSVC runtime: {filename}")
        bundled_hash = _sha256(bundled)
        source_hash = _sha256(source)
        if bundled_hash != source_hash:
            raise RuntimeError(f"MSVC runtime не совпадает с PySide6: {filename}")
        runtime[filename] = {"source": str(source), "sha256": bundled_hash}

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "collect_toc": str(toc_path),
        "binary_entries": len(entries),
        "foreign_binary_origins": [],
        "trusted_roots": [str(root) for root in trusted_roots],
        "pyside_msvc_runtime": runtime,
    }
    report_path = build_root / "BUILD_AUDIT.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"PASS: {len(entries)} binary entries, foreign origins: 0")
    print(f"PASS: {len(runtime)} PySide6 MSVC runtime files match")
    print(f"Audit: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
