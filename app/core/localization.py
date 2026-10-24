from __future__ import annotations

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

RUSSIAN_LOCALE = QLocale(QLocale.Language.Russian, QLocale.Country.Russia)


def set_russian_qt_locale() -> None:
    QLocale.setDefault(RUSSIAN_LOCALE)


def install_russian_qt_translations(app: QApplication) -> bool:
    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    loaded = translator.load(RUSSIAN_LOCALE, "qtbase", "_", translations)
    if loaded:
        app.installTranslator(translator)
        app._russian_qt_translators = [translator]  # type: ignore[attr-defined]
    return loaded
