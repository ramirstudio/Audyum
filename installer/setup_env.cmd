@echo off
setlocal
cd /d "%~dp0"

echo.
echo  Audyum: preparo Python 3.11, PyTorch con CUDA 12.8 e MMAudio.
echo  Sono circa 4 GB da scaricare, possono servire diversi minuti.
echo.

rem Il venv e i pacchetti stanno nella cartella di installazione. Python gestito da uv va invece
rem fuori da qualsiasi cartella che OneDrive possa toccare: con Files On-Demand attivo Windows
rem rifiuta i collegamenti che uv crea (errore 448). Primo tentativo in AppData\Local, poi in Public.
rem Resti di un tentativo precedente fallito (collegamenti non attraversabili): si rimuovono.
if exist "%~dp0python" rmdir /s /q "%~dp0python" >nul 2>&1
if exist "%~dp0.venv" rmdir /s /q "%~dp0.venv" >nul 2>&1
rem Giunzioni lasciate da versioni di uv piu' recenti: uv 0.7 le trova e fallisce. Via tutto.
for %%D in ("%LOCALAPPDATA%\Audyum\uv" "%PUBLIC%\Audyum\uv") do if exist "%%~D" rmdir /s /q "%%~D" >nul 2>&1

set "UV_PROJECT_ENVIRONMENT=%~dp0.venv"
set "UV_LINK_MODE=copy"
set "UV_PYTHON_PREFERENCE=only-managed"
set "FROZEN="
if exist "%~dp0uv.lock" set "FROZEN=--frozen"

rem Cartelle usate dalle versioni precedenti: dentro ci sono collegamenti che Windows non legge piu'.
if exist "%LOCALAPPDATA%\Audyum\uv" rmdir /s /q "%LOCALAPPDATA%\Audyum\uv" >nul 2>&1
if exist "%PUBLIC%\Audyum\uv" rmdir /s /q "%PUBLIC%\Audyum\uv" >nul 2>&1

set "UVROOT=%LOCALAPPDATA%\Audyum\py"
if exist "%UVROOT%" rmdir /s /q "%UVROOT%" >nul 2>&1
call :sync
if not errorlevel 1 goto ok

echo.
echo  Primo tentativo non riuscito, riprovo in una cartella diversa.
echo.
set "UVROOT=%PUBLIC%\Audyum\py"
if exist "%UVROOT%" rmdir /s /q "%UVROOT%" >nul 2>&1
call :sync
if not errorlevel 1 goto ok

echo.
echo  Preparazione non riuscita. Controlla la connessione e riprova da
echo  menu Start, "Audyum - ripara installazione". Se l'errore si ripete,
echo  mandalo a chi mantiene il programma.
echo.
pause
exit /b 1

:ok
rem La cache contiene una seconda copia delle wheel di torch: non serve piu'.
"%~dp0bin\uv.exe" cache clean >nul 2>&1
exit /b 0

:sync
set "UV_DATA_DIR=%UVROOT%"
set "UV_PYTHON_INSTALL_DIR=%UVROOT%\python"
set "UV_PYTHON_BIN_DIR=%UVROOT%\bin"
set "UV_CACHE_DIR=%UVROOT%\cache"
"%~dp0bin\uv.exe" sync %FROZEN% --no-dev --python 3.11
exit /b %errorlevel%
