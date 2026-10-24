from __future__ import annotations

import json
import re
import shutil
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QProcess, Signal

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def extract_json_payload(text: str) -> Any:
    clean = ANSI_ESCAPE.sub("", text).strip()
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, Any]] = []
    for match in re.finditer(r"[\[{]", clean):
        try:
            value, end = decoder.raw_decode(clean[match.start() :])
        except JSONDecodeError:
            continue
        candidates.append((match.start() + end, value))
    if not candidates:
        raise ValueError("PowerShell не вернул структурированный JSON.")
    return max(candidates, key=lambda item: item[0])[1]


def build_router_arguments(
    script: Path, command: str, node: str | None = None, different_ip: bool = False
) -> list[str]:
    arguments = ["-NoProfile", "-NonInteractive", "-File", str(script), command]
    if node:
        arguments.append(node)
    arguments.append("-Json")
    if different_ip:
        arguments.append("-DifferentIp")
    return arguments


class RouterProcess(QObject):
    started = Signal(str)
    progress = Signal(str)
    completed = Signal(str, object, str, int)

    def __init__(self, script: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.script = script
        self._process: QProcess | None = None
        self._command = ""
        self._stdout = ""
        self._stderr = ""
        self._line_buffer = ""

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def run(self, command: str, node: str | None = None, different_ip: bool = False) -> bool:
        if self.is_running:
            return False
        if not self.script.is_file():
            self.completed.emit(command, None, f"Не найден {self.script.name}", 1)
            return False

        program = shutil.which("pwsh.exe") or shutil.which("pwsh")
        if not program:
            self.completed.emit(command, None, "Не найден PowerShell 7 (pwsh.exe).", 1)
            return False

        self._command = command
        self._stdout = ""
        self._stderr = ""
        self._line_buffer = ""
        process = QProcess(self)
        self._process = process
        process.setWorkingDirectory(str(self.script.parent))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.errorOccurred.connect(self._on_error)
        process.finished.connect(self._on_finished)
        process.start(program, build_router_arguments(self.script, command, node, different_ip))
        self.started.emit(command)
        return True

    def _read_stdout(self) -> None:
        if self._process is None:
            return
        chunk = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout += chunk
        self._line_buffer += chunk
        lines = self._line_buffer.splitlines(keepends=True)
        self._line_buffer = ""
        for line in lines:
            if line.endswith(("\n", "\r")):
                clean = line.strip()
                if clean.startswith("Testing:"):
                    self.progress.emit(clean.replace("Testing:", "Проверяется:", 1))
            else:
                self._line_buffer = line

    def _read_stderr(self) -> None:
        if self._process is None:
            return
        self._stderr += bytes(self._process.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )

    def _on_error(self, _error: QProcess.ProcessError) -> None:
        if self._process is None:
            return
        if not self._stderr:
            self._stderr = self._process.errorString()
        if (
            _error == QProcess.ProcessError.FailedToStart
            and self._process.state() == QProcess.ProcessState.NotRunning
        ):
            command = self._command
            error = self._stderr
            process = self._process
            self._process = None
            process.deleteLater()
            self.completed.emit(command, None, error, 1)

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._read_stdout()
        self._read_stderr()
        command = self._command
        payload: Any = None
        error = ANSI_ESCAPE.sub("", self._stderr).strip()
        try:
            payload = extract_json_payload(self._stdout)
        except ValueError as exc:
            if exit_code == 0:
                error = str(exc)
                exit_code = 1
        if exit_code != 0 and not error:
            error = ANSI_ESCAPE.sub("", self._stdout).strip() or "Команда завершилась с ошибкой."

        process = self._process
        self._process = None
        if process is not None:
            process.deleteLater()
        self.completed.emit(command, payload, error, exit_code)
