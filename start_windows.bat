@echo off
setlocal
cd /d "%~dp0"
title Arman Launcher
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher not found. Install Python Launcher or run py -3 service.py manually.
  pause
  exit /b 1
)
start "Arman Server" "%ComSpec%" /k "py -3 service.py"
for /l %%i in (1,1,20) do (
  powershell -NoProfile -Command "try { $null=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/ -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>nul
  if not errorlevel 1 goto browser
  timeout /t 1 /nobreak >nul
)
echo Server did not respond. Read the Arman Server window for the error.
pause
exit /b 1
:browser
start "" "http://127.0.0.1:8765/"
endlocal
