@echo off
setlocal enabledelayedexpansion

REM ClaudeOS - Add to PATH
REM Run as administrator to install for all users, or run normally for current user.

echo.
echo ===================================
echo   ClaudeOS - PATH Setup
echo ===================================
echo.

set "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Check if already in PATH
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
echo %USER_PATH% | findstr /i /c:"%SCRIPT_DIR%" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] %SCRIPT_DIR% is already in your PATH.
    echo.
    echo  Usage: Open any folder in Explorer, type "cos" in the address bar.
    echo.
    pause
    exit /b 0
)

echo  Will add to PATH:
echo    %SCRIPT_DIR%
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorlevel% equ 0 (
    echo  [Admin] Installing for all users...
    setx PATH "%PATH%;%SCRIPT_DIR%" /M >nul 2>&1
    if !errorlevel! neq 0 (
        echo  [Failed] Could not set system PATH. Trying user PATH...
        goto :user_path
    )
    echo  [Done] Added to system PATH.
) else (
    :user_path
    echo  [User] Installing for current user...
    if defined USER_PATH (
        setx PATH "%USER_PATH%;%SCRIPT_DIR%" >nul 2>&1
    ) else (
        setx PATH "%SCRIPT_DIR%" >nul 2>&1
    )
    if !errorlevel! neq 0 (
        echo  [Failed] Could not set user PATH.
        pause
        exit /b 1
    )
    echo  [Done] Added to user PATH.
)

echo.
echo  ===================================
echo   Setup complete!
echo  ===================================
echo.
echo  Next steps:
echo   1. Open a NEW terminal/Explorer for PATH to take effect
echo   2. Navigate to your project folder in Explorer
echo   3. Type "cos" in the address bar to start
echo.
echo  Or from terminal:
echo   cos "C:\path\to\project"
echo.

pause
