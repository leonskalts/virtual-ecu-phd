@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

set "PYTHON_BIN=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_BIN=.venv\Scripts\python.exe"
)

if not exist "virtual_ecu.exe" if not exist "virtual_ecu" (
    echo virtual_ecu executable was not found.
    echo Native Windows builds require a compatible C toolchain and make.
    echo Recommended: use WSL Ubuntu and run:
    echo   bash scripts/setup_local.sh
    echo   bash scripts/launch_gui.sh
    echo.
)

"%PYTHON_BIN%" scripts\virtual_ecu_gui.py
if errorlevel 1 (
    echo.
    echo Failed to launch the GUI. Ensure Python is installed and dependencies are available.
    echo Recommended setup on Windows: use WSL Ubuntu and follow INSTALL.md.
)

endlocal
