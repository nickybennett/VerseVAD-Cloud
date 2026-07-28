@echo off
setlocal
cd /d "%~dp0"

set "VERSEVAD_UV=%~dp0.tools\uv\uv.exe"
set "UV_CACHE_DIR=%~dp0.runtime\uv-cache"
set "UV_PYTHON_INSTALL_DIR=%~dp0.runtime\python"
set "UV_PYTHON_INSTALL_REGISTRY=0"
set "UV_PYTHON_PREFERENCE=only-managed"

if not exist "%VERSEVAD_UV%" (
  echo VerseVAD's local setup tool is missing.
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)

echo Updating the VerseMap reference-corpus manifest...
"%VERSEVAD_UV%" run --frozen --offline versevad-update-versemap
set "VERSEMAP_STATUS=%ERRORLEVEL%"

echo.
if not "%VERSEMAP_STATUS%"=="0" (
  echo The updater found a problem. Review the messages above.
) else (
  echo The reference release is ready for review and source control.
)
echo.
pause
exit /b %VERSEMAP_STATUS%
