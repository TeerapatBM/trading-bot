@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\install-vps.ps1"
if errorlevel 1 (
  echo.
  echo Installation did not complete. See the error above.
)
pause
