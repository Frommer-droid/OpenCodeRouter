@echo off
cd /d "%~dp0"
if not exist "%~dp0OpenCodeRouter.ps1" exit /b 1
pwsh.exe -NoProfile -NoExit -File "%~dp0OpenCodeRouter.ps1" menu
