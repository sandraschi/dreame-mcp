@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"
echo.
echo === Script exited with code %ERRORLEVEL% ===
pause
