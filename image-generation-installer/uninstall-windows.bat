@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

start "Custom Image Generation Uninstaller" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -NoExit -File "%SCRIPT_DIR%uninstall-windows.ps1" %*

endlocal
