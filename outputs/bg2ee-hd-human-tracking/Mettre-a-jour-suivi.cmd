@echo off
setlocal
chcp 65001 >nul

set "UPDATE_SCRIPT=%~dp0..\..\pipeline\scripts\Update-HumanTrackingWorkbook.ps1"
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%UPDATE_SCRIPT%"
set "UPDATE_EXIT_CODE=%ERRORLEVEL%"

echo.
if "%UPDATE_EXIT_CODE%"=="0" (
  echo Le classeur est a jour. Vous pouvez le rouvrir dans Excel.
) else (
  echo La mise a jour a echoue. Consultez le message ci-dessus.
)
echo.
pause
exit /b %UPDATE_EXIT_CODE%
