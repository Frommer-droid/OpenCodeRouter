@echo off
cd /d "%~dp0"
set "ROUTER_PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%ROUTER_PYTHONW%" (
  echo Python environment is missing. Follow the setup steps in README.md.
  pause
  exit /b 1
)
if not exist "%~dp0OpenCodeRouter.pyw" exit /b 1
start "" /D "%~dp0" "%ROUTER_PYTHONW%" "%~dp0OpenCodeRouter.pyw" %*
