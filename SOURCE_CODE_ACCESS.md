# Доступ к исходному коду сторонних библиотек

Исходный код PySide6 и Qt, соответствующий включённым двоичным компонентам, доступен в официальных репозиториях Qt Company:

- PySide6 / Shiboken: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt 6: https://code.qt.io/cgit/qt/qt5.git/

Точная версия PySide6 и перечень Qt DLL фиксируются в `RUNTIME_MANIFEST.json` каждой сборки. OpenCode Router не содержит модифицированной версии PySide6 или Qt. Библиотеки размещены раздельно в каталоге `_internal`, что сохраняет возможность их замены совместимыми файлами пользователем.
