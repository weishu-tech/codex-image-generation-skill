@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

start "Custom Image Generation Installer" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -NoExit -File "%SCRIPT_DIR%install-windows.ps1" %*

endlocal
