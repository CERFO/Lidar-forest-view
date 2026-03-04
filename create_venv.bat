@echo off
setlocal
REM Script directory (with trailing backslash); venv created in same folder as this .bat
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
cd /d "%SCRIPT_DIR%"

echo [create_venv] Working directory: %SCRIPT_DIR%
echo.

if exist "%VENV_DIR%" (
    echo [create_venv] Virtual environment already exists at: %VENV_DIR%
    echo To recreate it, delete the .venv folder and run this script again.
    echo.
    pause
    exit /b 0
)

echo [create_venv] Creating virtual environment at: %VENV_DIR%
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [create_venv] ERROR: Failed to create venv. Ensure Python is installed and on PATH.
    echo Try running "python --version" in a terminal.
    echo.
    pause
    exit /b 1
)
echo [create_venv] Venv created successfully.
echo.

echo [create_venv] Upgrading pip and installing dependencies from requirements.txt ...
call "%VENV_DIR%\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [create_venv] ERROR: Failed to install requirements.
    echo.
    pause
    exit /b 1
)

echo.
echo [create_venv] Done. Virtual environment is ready at: %VENV_DIR%
echo Use run_app.bat to start the application.
echo.
pause
endlocal
