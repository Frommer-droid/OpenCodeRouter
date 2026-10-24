from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def minimal_build_environment(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    venv_root = project_root / ".venv"
    base_prefix = Path(sys.base_prefix).resolve()
    system_root = Path(env.get("SystemRoot", r"C:\Windows")).resolve()
    candidates = (
        venv_root / "Scripts",
        venv_root / "Lib" / "site-packages" / "PySide6",
        venv_root / "Lib" / "site-packages" / "shiboken6",
        base_prefix,
        base_prefix / "DLLs",
        system_root / "System32",
    )
    env["PATH"] = os.pathsep.join(str(path) for path in candidates if path.is_dir())
    env["PYTHONUTF8"] = "1"
    return env


def main() -> int:
    build_tools = Path(__file__).resolve().parent
    project_root = build_tools.parent
    expected_python = (project_root / ".venv" / "Scripts" / "python.exe").resolve()
    build_root = Path(os.environ.get("OPENCODE_ROUTER_BUILD_ROOT", project_root.parent / "temp-dev" / project_root.name / "release"))
    if Path(sys.executable).resolve() != expected_python:
        raise RuntimeError(f"Сборку нужно запускать через {expected_python}")

    command = [
        str(expected_python),
        "-m",
        "PyInstaller",
        str(build_tools / "OpenCodeRouter.spec"),
        "--noconfirm",
        "--distpath",
        str(build_root / "dist"),
        "--workpath",
        str(build_root / "build"),
    ]
    subprocess.run(
        command,
        cwd=project_root,
        env=minimal_build_environment(project_root),
        check=True,
    )
    subprocess.run(
        [str(expected_python), str(build_tools / "audit_build.py")],
        cwd=project_root,
        env=minimal_build_environment(project_root),
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
