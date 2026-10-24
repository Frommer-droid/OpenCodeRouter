from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import tempfile
from ctypes import wintypes
from pathlib import Path

BUNDLE_NAME = "OpenCodeRouter"
DISPLAY_NAME = "OpenCode Router"
PUBLISHER = "Frommer"
APP_ID = "{{E56B98D8-10AC-4F3A-86A8-C9870F325F1C}"


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def resolve_desktop() -> Path:
    override = os.environ.get("OPENCODE_ROUTER_INSTALLER_DIR", "").strip()
    if override:
        return Path(override).resolve()
    try:
        import winreg

        key_name = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(os.path.expandvars(value)).resolve()
    except (OSError, ValueError):
        pass
    try:
        folder_id = GUID(
            0xB4BFCC3A,
            0xDB2C,
            0x424C,
            (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41),
        )
        result = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, None, ctypes.byref(result)
        ) == 0:
            try:
                return Path(result.value).resolve()
            finally:
                ctypes.windll.ole32.CoTaskMemFree(result)
    except (AttributeError, OSError, ValueError):
        pass
    return (Path.home() / "Desktop").resolve()


def local_build_settings() -> dict:
    path = Path(__file__).resolve().parents[1] / "private" / "build-settings.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def default_install_dir() -> str:
    return "{code:GetDefaultDir}"


def find_iscc() -> Path:
    local_iscc = local_build_settings().get("iscc")
    candidates = (
        Path(os.environ["INNO_SETUP_ISCC"]) if os.environ.get("INNO_SETUP_ISCC") else None,
        Path(local_iscc) if local_iscc else None,
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
    )
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError("ISCC.exe не найден: установите Inno Setup 6 или задайте INNO_SETUP_ISCC")


def iss_text(source: Path, output: Path, version: str) -> str:
    icon = source / "assets" / "router.ico"
    install = default_install_dir()
    return f'''#define MyAppName "{DISPLAY_NAME}"
#define MyAppVersion "{version}"
#define MyAppExeName "{BUNDLE_NAME}.exe"

[Setup]
AppId={APP_ID}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={PUBLISHER}
DefaultDirName="{install}"
UsePreviousAppDir=no
LanguageDetectionMethod=none
ShowLanguageDialog=no
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir="{output}"
OutputBaseFilename={BUNDLE_NAME}_v{{#MyAppVersion}}_Setup
SetupIconFile="{icon}"
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
VersionInfoVersion={{#MyAppVersion}}.0
VersionInfoCompany={PUBLISHER}
VersionInfoProductName={{#MyAppName}}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: checkedonce

[Dirs]
Name: "{{app}}"; Permissions: users-modify

[Files]
Source: "{source}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\assets\\router.ico"
Name: "{{group}}\\Удалить {{#MyAppName}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\assets\\router.ico"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "Запустить {{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM {{#MyAppExeName}}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}"

[Code]
function GetDefaultDir(Param: String): String;
begin
  if DirExists('D:\\') then
    Result := 'D:\\Apps\\{BUNDLE_NAME}'
  else
    Result := 'C:\\Apps\\{BUNDLE_NAME}';
end;
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent
    source = Path(os.environ.get("OPENCODE_ROUTER_BUNDLE_DIR", project_root / BUNDLE_NAME))
    required = (
        source / f"{BUNDLE_NAME}.exe",
        source / "_internal",
        source / "VERSION",
        source / "RUNTIME_MANIFEST.json",
        source / "BUILD_AUDIT.json",
        source / "OpenCodeRouter.config.example.json",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Неполная release-папка:\n" + "\n".join(missing))
    version = (source / "VERSION").read_text(encoding="utf-8").strip()
    output = (args.output_dir or resolve_desktop()).resolve()
    output.mkdir(parents=True, exist_ok=True)
    build_root = Path(os.environ.get("OPENCODE_ROUTER_BUILD_ROOT", project_root.parent / "temp-dev" / project_root.name / "release"))
    build_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="installer-", dir=build_root) as temp:
        iss = Path(temp) / "OpenCodeRouter.iss"
        iss.write_text(iss_text(source, output, version), encoding="utf-8-sig")
        subprocess.run([str(find_iscc()), str(iss)], check=True)
    installer = output / f"{BUNDLE_NAME}_v{version}_Setup.exe"
    if not installer.is_file():
        raise FileNotFoundError(f"Установщик не создан: {installer}")
    print(installer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
