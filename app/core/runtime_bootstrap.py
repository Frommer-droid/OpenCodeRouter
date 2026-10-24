from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


def project_pythonw(project_root: Path) -> Path | None:
    candidate = project_root.resolve() / ".venv" / "Scripts" / "pythonw.exe"
    return candidate if candidate.is_file() else None


def relaunch_with_project_pythonw(
    project_root: Path,
    entrypoint: Path,
    arguments: Sequence[str],
    current_executable: Path,
    *,
    frozen: bool,
) -> bool:
    if frozen:
        return False
    pythonw = project_pythonw(project_root)
    if pythonw is None:
        return False
    if pythonw.resolve() == current_executable.resolve():
        return False
    subprocess.Popen(
        [str(pythonw), str(entrypoint.resolve()), *arguments],
        cwd=str(project_root.resolve()),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )
    return True
