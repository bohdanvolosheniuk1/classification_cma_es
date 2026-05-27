@echo off
REM Запуск MLflow UI на http://localhost:5000
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Не вдалось активувати venv.
    pause
    exit /b 1
)
echo MLflow UI: http://localhost:5000
mlflow ui
pause >nul
