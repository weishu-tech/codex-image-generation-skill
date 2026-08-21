@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

start "CCWS Image Generation Uninstaller" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -NoExit -File "%SCRIPT_DIR%uninstall-windows.ps1" %*

endlocal
