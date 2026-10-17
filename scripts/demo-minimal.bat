@echo off
setlocal
cd /d "%~dp0.."
set "ARCHIVE=%TEMP%\vfs-shell-minimal-%RANDOM%.zip"

python scripts\create_demo_vfs.py --profile minimal --output "%ARCHIVE%"
if errorlevel 1 (
    del "%ARCHIVE%" >nul 2>nul
    pause
    exit /b 1
)
python -m src.cli --vfs "%ARCHIVE%" --script scripts\demo-minimal.commands
set "RESULT=%ERRORLEVEL%"
del "%ARCHIVE%" >nul 2>nul
echo.
pause
exit /b %RESULT%
