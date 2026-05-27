@echo off
REM Launch Streamlit dashboard. Double-click to run.
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: .venv folder not found.
    echo Run setup first: py -3 -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -e .
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Starting Streamlit on http://localhost:8501
echo Close this window to stop the server.
echo.
streamlit run app.py
echo.
echo Server stopped. Press any key to exit.
pause >nul
