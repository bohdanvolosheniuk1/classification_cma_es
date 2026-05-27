@echo off
REM Launch MLflow UI on http://localhost:5000
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: .venv folder not found.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo MLflow UI: http://localhost:5000
echo Close this window to stop.
echo.
mlflow ui
pause >nul
