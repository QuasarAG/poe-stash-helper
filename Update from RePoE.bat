@echo off
setlocal
set PYTHONDONTWRITEBYTECODE=1
title PoE Stash Helper - Update Databases
cd /d "%~dp0"

echo ============================================================
echo  PoE Stash Helper - Full Database Rebuild
echo  Source: repoe-fork.github.io (GGG official data mirror)
echo ============================================================
echo.
echo  Rebuilding:
echo    1. Base item types  -^>  data/base_types.json
echo    2. Mod tier ranges  -^>  data/mod_data.py
echo.
echo  Options you can pass:
echo    --force-fetch   bypass 24h cache and re-download everything
echo    --mods          rebuild mod tiers only
echo    --bases         rebuild base items only
echo    --dry           dry-run (parse only, no writes)
echo ============================================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON=python
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON=py
    ) else (
        echo  [ERROR] Python not found.
        echo  Install Python 3.9+ and make sure it is on your PATH.
        echo.
        pause
        exit /b 1
    )
)

echo  Using: %PYTHON%
echo.

%PYTHON% tools\update_all.py %*

echo.
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Update failed. See error above.
) else (
    echo  Done. Restart the app to load the new data.
)
echo.
pause
endlocal
