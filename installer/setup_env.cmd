@echo off
setlocal
cd /d "%~dp0"

rem Tutto resta dentro la cartella di installazione: Python gestito da uv, ambiente virtuale, pacchetti.
set "UV_PYTHON_INSTALL_DIR=%~dp0python"
set "UV_PROJECT_ENVIRONMENT=%~dp0.venv"
set "UV_CACHE_DIR=%LOCALAPPDATA%\Audyum\uv-cache"
set "UV_LINK_MODE=copy"
set "UV_PYTHON_PREFERENCE=only-managed"

echo.
echo  Audyum: preparo Python 3.11, PyTorch con CUDA 12.8 e MMAudio.
echo  Sono circa 4 GB da scaricare, possono servire diversi minuti.
echo.

set "FROZEN="
if exist "%~dp0uv.lock" set "FROZEN=--frozen"
"%~dp0bin\uv.exe" sync %FROZEN% --no-dev --python 3.11
if errorlevel 1 goto fail

rem La cache contiene una seconda copia delle wheel di torch: non serve piu'.
"%~dp0bin\uv.exe" cache clean >nul 2>&1
exit /b 0

:fail
echo.
echo  Preparazione non riuscita. Controlla la connessione e riprova da
echo  menu Start, "Audyum - ripara installazione".
echo.
pause
exit /b 1
