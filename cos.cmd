@echo off
REM ClaudeOS Launcher
REM Usage: type "cos" in Explorer address bar to use current folder as workspace
REM        or double-click to use default "project" folder
python "%~dp0orchestrator.py" "%cd%"
if %errorlevel% neq 0 (
    echo.
    echo [Error] Failed to start ClaudeOS. Error code: %errorlevel%
    pause
)
