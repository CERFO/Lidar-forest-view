@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "PYTHONW=%VENV_DIR%\Scripts\pythonw.exe"
cd /d "%SCRIPT_DIR%"

if not exist "%PYTHONW%" (
    echo Virtual environment not found at: %VENV_DIR%
    echo Run create_venv.bat first.
    echo.
    pause
    exit /b 1
)

start "" "%PYTHONW%" main.py %*
endlocal
