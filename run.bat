@echo off
cd /d "%~dp0"
python -m src.cli %*
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
