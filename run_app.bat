@echo off
REM Запуск Streamlit-дашборду. Подвiйний клiк - запуск.
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Не вдалось активувати venv. Перевірте що тека .venv існує.
    pause
    exit /b 1
)
echo Запускаю Streamlit...
streamlit run app.py
echo.
echo Сервер зупинено. Натисніть будь-яку клавішу для виходу.
pause >nul
