from pathlib import Path

from app.core.runtime_bootstrap import project_pythonw, relaunch_with_project_pythonw


def test_project_pythonw_prefers_repository_venv(tmp_path) -> None:
    candidate = tmp_path / ".venv" / "Scripts" / "pythonw.exe"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    assert project_pythonw(tmp_path) == candidate


def test_project_pythonw_does_not_fall_back_to_global_python(tmp_path) -> None:
    assert project_pythonw(tmp_path) is None


def test_no_relaunch_when_already_using_project_pythonw(tmp_path, monkeypatch) -> None:
    candidate = tmp_path / ".venv" / "Scripts" / "pythonw.exe"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    called = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("app.core.runtime_bootstrap.subprocess.Popen", fail_if_called)
    relaunched = relaunch_with_project_pythonw(
        tmp_path,
        tmp_path / "OpenCodeRouter.pyw",
        [],
        candidate,
        frozen=False,
    )
    assert not relaunched
    assert not called


def test_global_python_relaunches_project_pythonw(tmp_path, monkeypatch) -> None:
    candidate = tmp_path / ".venv" / "Scripts" / "pythonw.exe"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    captured: dict[str, object] = {}

    def capture(command, **kwargs) -> None:
        captured["command"] = command
        captured.update(kwargs)

    monkeypatch.setattr("app.core.runtime_bootstrap.subprocess.Popen", capture)
    relaunched = relaunch_with_project_pythonw(
        tmp_path,
        tmp_path / "OpenCodeRouter.pyw",
        ["--smoke-test"],
        Path("C:/Python312/python.exe"),
        frozen=False,
    )
    assert relaunched
    assert captured["command"][0] == str(candidate)
    assert captured["command"][2] == "--smoke-test"
