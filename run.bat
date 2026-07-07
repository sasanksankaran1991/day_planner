@echo off
REM Day Planner — Windows launcher (double-click or run from cmd)
cd /d "%~dp0"

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe run.py %*
) else (
    python run.py %*
)

if errorlevel 1 pause
