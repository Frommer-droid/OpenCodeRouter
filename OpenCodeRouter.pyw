from __future__ import annotations

import ctypes
import multiprocessing
import sys
import traceback
from pathlib import Path

from app.core.runtime_bootstrap import relaunch_with_project_pythonw


def _relaunch_with_pythonw() -> bool:
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return False
    entrypoint = Path(__file__).resolve()
    return relaunch_with_project_pythonw(
        project_root=entrypoint.parent,
        entrypoint=entrypoint,
        arguments=sys.argv[1:],
        current_executable=Path(sys.executable),
        frozen=False,
    )
    return True


if _relaunch_with_pythonw():
    raise SystemExit(0)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.app_config import (  # noqa: E402
    APP_ICON,
    APP_NAME,
    APP_USER_MODEL_ID,
    APP_VERSION,
    LOG_FILE,
)
from app.core.application import ApplicationCore  # noqa: E402
from app.core.localization import (  # noqa: E402
    install_russian_qt_translations,
    set_russian_qt_locale,
)
from app.ui.main_window import MainWindow  # noqa: E402
from app.utils.logging_utils import configure_logging, shutdown_logging  # noqa: E402


def _set_windows_app_id() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except OSError:
            pass


def _render_smoke_path() -> Path | None:
    prefix = "--render-smoke="
    for argument in sys.argv:
        if argument.startswith(prefix):
            return Path(argument[len(prefix) :]).resolve()
    return None


def main() -> int:
    logger = configure_logging(LOG_FILE)
    try:
        logger.info("Runtime Python: %s", sys.executable)
        _set_windows_app_id()
        set_russian_qt_locale()
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("Frommer")
        app.setQuitOnLastWindowClosed(False)
        install_russian_qt_translations(app)

        icon = QIcon(str(APP_ICON))
        if not icon.isNull():
            app.setWindowIcon(icon)
        core = ApplicationCore(logger)
        smoke_mode = "--smoke-test" in sys.argv or _render_smoke_path() is not None
        window = MainWindow(core, auto_start=not smoke_mode)
        if not icon.isNull():
            window.setWindowIcon(icon)

        render_path = _render_smoke_path()
        if render_path is not None:
            def save_smoke_image() -> None:
                render_path.parent.mkdir(parents=True, exist_ok=True)
                window.grab().save(str(render_path))
                app.quit()

            QTimer.singleShot(500, save_smoke_image)
        elif smoke_mode:
            QTimer.singleShot(500, app.quit)
        return app.exec()
    except Exception:
        logger.critical("Необработанная ошибка:\n%s", traceback.format_exc())
        return 1
    finally:
        shutdown_logging()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
