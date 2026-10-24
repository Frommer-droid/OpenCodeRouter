# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa: E402, F821, I001
from __future__ import annotations

import os
import sys

import PySide6
from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo,
)

spec_dir = os.path.abspath(globals()["SPECPATH"])
if spec_dir not in sys.path:
    sys.path.insert(0, spec_dir)

from runtime_dll_policy import (
    build_trusted_binary_roots,
    prefer_pyside_msvc_runtime,
    validate_trusted_binary_origins,
)


APP_NAME = "OpenCodeRouter"
ENTRYPOINT = "OpenCodeRouter.pyw"
EXTRA_TRUSTED_BINARY_ROOTS: tuple[str, ...] = ()

project_root = os.path.abspath(os.path.join(spec_dir, ".."))
pyside_root = os.path.dirname(PySide6.__file__)
with open(os.path.join(project_root, "VERSION"), encoding="utf-8") as version_file:
    app_version = version_file.read().strip()
version_tuple = tuple(int(part) for part in app_version.split(".")) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple,
                      mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable("040904B0", [
        StringStruct("FileDescription", "OpenCode Router"),
        StringStruct("FileVersion", app_version),
        StringStruct("ProductName", "OpenCode Router"),
        StringStruct("ProductVersion", app_version),
        StringStruct("OriginalFilename", "OpenCodeRouter.exe"),
    ])]), VarFileInfo([VarStruct("Translation", [1033, 1200])])],
)

ROOT_DATA_FILES = (
    "VERSION",
    "LICENSE",
    "OpenCodeRouter.ps1",
    "Router.Core.psm1",
    "NamedPipeHttp.cs",
    "OpenCodeRouter.config.example.json",
    "README.md",
    "RELEASE_NOTES.md",
    "THIRD_PARTY_NOTICES.md",
    "SOURCE_CODE_ACCESS.md",
    "QT_PYSIDE6_COMPLIANCE.md",
)

datas = []
for filename in ROOT_DATA_FILES:
    source = os.path.join(project_root, filename)
    if not os.path.isfile(source):
        raise FileNotFoundError(f"Обязательный release-файл отсутствует: {source}")
    datas.append((source, "."))

translation = os.path.join(pyside_root, "translations", "qtbase_ru.qm")
if not os.path.isfile(translation):
    translation = os.path.join(pyside_root, "Qt", "translations", "qtbase_ru.qm")
if not os.path.isfile(translation):
    raise FileNotFoundError("В PySide6 не найден qtbase_ru.qm")
datas.append((translation, os.path.join("PySide6", "translations")))

a = Analysis(
    [os.path.join(project_root, ENTRYPOINT)],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"],
    hookspath=[spec_dir],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "torch", "tensorflow"],
    noarchive=False,
)

validate_trusted_binary_origins(
    a.binaries,
    build_trusted_binary_roots(project_root, EXTRA_TRUSTED_BINARY_ROOTS),
)
a.binaries = prefer_pyside_msvc_runtime(a.binaries, pyside_root)
validate_trusted_binary_origins(
    a.binaries,
    build_trusted_binary_roots(project_root, EXTRA_TRUSTED_BINARY_ROOTS),
)
a.datas += Tree(os.path.join(project_root, "assets"), prefix="assets")

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(project_root, "assets", "router.ico"),
    version=version_info,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
