@echo off
setlocal
cd /d "%~dp0.."
set "ARCHIVE=%TEMP%\vfs-shell-nested-%RANDOM%.zip"

python scripts\create_demo_vfs.py --profile nested --output "%ARCHIVE%"
if errorlevel 1 (
    del "%ARCHIVE%" >nul 2>nul
    exit /b 1
)
python -m src.cli --vfs "%ARCHIVE%" --script scripts\demo-nested.commands
set "RESULT=%ERRORLEVEL%"
del "%ARCHIVE%" >nul 2>nul
exit /b %RESULT%
