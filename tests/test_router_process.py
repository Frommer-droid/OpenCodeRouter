import json
import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QProcess

from app.services.router_process import build_router_arguments, extract_json_payload

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_extracts_json_after_auto_progress() -> None:
    output = 'Testing: A\nTesting: Б\n{"node":"Б","ok":true,"checks":[]}'
    assert extract_json_payload(output)["node"] == "Б"


def test_extracts_list_payload() -> None:
    assert extract_json_payload('[{"Node":"A"},{"Node":"B"}]')[1]["Node"] == "B"


def test_rejects_output_without_json() -> None:
    with pytest.raises(ValueError, match="JSON"):
        extract_json_payload("controller unavailable")


def test_builds_safe_powershell_arguments_for_unicode_node() -> None:
    script = Path("C:/test-project/OpenCodeRouter.ps1")
    arguments = build_router_arguments(script, "use", "🇩🇪 Германия ⭐️")
    assert arguments == [
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(script),
        "use",
        "🇩🇪 Германия ⭐️",
        "-Json",
    ]


def test_router_module_forces_utf8_stdout_for_qprocess() -> None:
    program = shutil.which("pwsh.exe") or shutil.which("pwsh")
    if not program:
        pytest.skip("Для проверки кодировки требуется PowerShell 7.")

    module = str(PROJECT_ROOT / "Router.Core.psm1").replace("'", "''")
    node = "🇩🇪 Германия ⭐️"
    command = (
        "$ErrorActionPreference='Stop'; "
        f"Import-Module '{module}' -Force -DisableNameChecking; "
        f"[pscustomobject]@{{Node='{node}'}} | ConvertTo-Json -Compress"
    )
    process = QProcess()
    process.start(program, ["-NoProfile", "-NonInteractive", "-Command", command])

    assert process.waitForFinished(10_000), process.errorString()
    stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
    assert process.exitCode() == 0, stderr
    payload = json.loads(bytes(process.readAllStandardOutput()).decode("utf-8"))
    assert payload["Node"] == node
