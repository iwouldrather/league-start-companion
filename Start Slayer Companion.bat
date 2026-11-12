@echo off
setlocal
cd /d "%~dp0"
set "SLAYER_PYTHON=C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1110-973-0_26.1110.973.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe"
if exist "%SLAYER_PYTHON%" (
    "%SLAYER_PYTHON%" "%~dp0scripts\dev-server.py"
) else (
    py -3 "%~dp0scripts\dev-server.py"
)
if errorlevel 1 pause
