# OpenCode Router development handoff

Version: 0.3.4. Status: released source, 2026-10-24.

Russia is excluded from selectable locations by country names, flag and RU/RUS
codes in subscription names. The shared filter covers GUI/CLI lists, scan, auto,
DifferentIp and manual use/test. IP geolocation is not checked.

PyInstaller validates native binary origins before and after MSVC replacement;
the complete MSVC runtime comes from PySide6. Builds preserve work and caches.

Verification: 38 pytest tests, Ruff, PowerShell regression/parser checks and Node
direction tests. See DEVELOPER.md and VERIFICATION.md for reproducible commands.
Use a project-local .venv and your own Clash configuration. No credentials or
local runtime settings are distributed. No pending implementation work.
