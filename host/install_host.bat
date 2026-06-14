@echo off
setlocal enabledelayedexpansion
:: install_host.bat — register the Harpe native messaging host on Windows.
::
::   install_host.bat
::
:: Writes the host manifest and points the per-user registry keys for Chrome,
:: Chromium, Edge, Brave and Firefox at it. Re-run any time. Needs Python on PATH.

set "HOST_NAME=com.nullsense.harpe"
set "DIR=%~dp0"
set "WRAPPER=%DIR%harpe_host.bat"
set "MANIFEST=%DIR%%HOST_NAME%.json"
set "FF_MANIFEST=%DIR%%HOST_NAME%.firefox.json"
set "EXT_ID=ginhcamellmffiamggkiaemdklcnechf"
set "GECKO_ID=harpe@nullsense.com"

where python >nul 2>nul || (echo ERROR: python not found on PATH & exit /b 1)

:: --- write the Chromium manifest (escape backslashes for JSON) ---
set "WPATH=%WRAPPER:\=\\%"
> "%MANIFEST%" (
  echo {
  echo   "name": "%HOST_NAME%",
  echo   "description": "Harpe native messaging host",
  echo   "path": "%WPATH%",
  echo   "type": "stdio",
  echo   "allowed_origins": [ "chrome-extension://%EXT_ID%/" ]
  echo }
)
:: --- write the Firefox manifest ---
> "%FF_MANIFEST%" (
  echo {
  echo   "name": "%HOST_NAME%",
  echo   "description": "Harpe native messaging host",
  echo   "path": "%WPATH%",
  echo   "type": "stdio",
  echo   "allowed_extensions": [ "%GECKO_ID%" ]
  echo }
)

:: --- point per-user registry keys at the manifests (HKCU) ---
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\%HOST_NAME%" /ve /t REG_SZ /d "%MANIFEST%" /f >nul
reg add "HKCU\Software\Chromium\NativeMessagingHosts\%HOST_NAME%" /ve /t REG_SZ /d "%MANIFEST%" /f >nul
reg add "HKCU\Software\Microsoft\Edge\NativeMessagingHosts\%HOST_NAME%" /ve /t REG_SZ /d "%MANIFEST%" /f >nul
reg add "HKCU\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\%HOST_NAME%" /ve /t REG_SZ /d "%MANIFEST%" /f >nul
reg add "HKCU\Software\Mozilla\NativeMessagingHosts\%HOST_NAME%" /ve /t REG_SZ /d "%FF_MANIFEST%" /f >nul

echo Harpe native host registered for Chrome, Chromium, Edge, Brave and Firefox.
echo Manifest: %MANIFEST%
echo Make sure 'harpe' is installed and on PATH (uv tool install harpe).
endlocal
