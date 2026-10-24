# Сторонние компоненты

OpenCode Router 0.3.1 включает Python runtime, PySide6/Qt for Python и их зависимости, собранные PyInstaller.

PySide6 6.11.2 распространяется по выбору получателя на условиях LGPL-3.0-only, GPL-2.0-only или GPL-3.0-only. В этой поставке предполагается использование варианта LGPL-3.0-only. Приложение не модифицирует PySide6 или Qt; библиотеки находятся отдельными файлами в `_internal` и могут быть заменены совместимой сборкой.

- Qt for Python: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt: https://code.qt.io/cgit/qt/qt5.git/
- GNU LGPL 3.0: https://www.gnu.org/licenses/lgpl-3.0.html
- PyInstaller: https://github.com/pyinstaller/pyinstaller

Собственный исходный код OpenCode Router распространяется под лицензией [MIT](LICENSE). Она не заменяет лицензии перечисленных сторонних компонентов.
