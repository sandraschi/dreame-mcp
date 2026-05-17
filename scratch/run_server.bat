@echo off
cd /d "%~dp0.."
.venv\Scripts\python.exe -m dreame_mcp --mode dual --port 10894
