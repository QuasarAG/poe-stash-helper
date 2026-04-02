@echo off
setlocal
set PYTHONDONTWRITEBYTECODE=1
cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON=python
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON=py
    ) else (
        echo.
        echo [ERROR] Python not found.
        echo Install Python 3.9+ and make sure it is on your PATH.
        echo.
        pause
        exit /b 1
    )
)

%PYTHON% main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Something went wrong. Press any key to see the error above.
    pause
)
endlocal
