@echo off
setlocal
cd /d "%~dp0"

set "PY="
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (
    echo No virtual environment found. Creating .venv ...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
    set "PY=.venv\Scripts\python.exe"
)

"%PY%" -c "import fastapi, uvicorn, prometheus_client" >nul 2>&1
if errorlevel 1 (
    echo Installing backend dependencies ...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)

echo Starting Parts Search API on http://127.0.0.1:8000 (docs at /docs)
"%PY%" -m uvicorn app.main:app --reload
pause
