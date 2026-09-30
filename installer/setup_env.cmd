@echo off
setlocal
cd /d "%~dp0"

echo.
echo  Audyum: preparo Python 3.11, PyTorch con CUDA 12.8 e MMAudio.
echo  Servono circa 4 GB di download e 15 GB liberi sul disco di installazione durante l'operazione.
echo.

rem Resti di tentativi precedenti (anche su C:): si cancellano per liberare spazio.
if exist "%~dp0python" rmdir /s /q "%~dp0python" >nul 2>&1
for %%D in ("%LOCALAPPDATA%\Audyum\uv" "%LOCALAPPDATA%\Audyum\py" "%PUBLIC%\Audyum\uv" "%PUBLIC%\Audyum\py") do if exist "%%~D" rmdir /s /q "%%~D" >nul 2>&1

rem Segnala al programma che e' installato: modelli e log vanno in <cartella>\data.
echo installato> "%~dp0portable.txt"

rem Python di uv e cache stanno nella cartella di installazione (stesso disco del venv). La cache NON viene svuotata se qualcosa va storto:
rem un nuovo tentativo riparte dai pacchetti gia' scaricati. I file si collegano con hardlink
rem (nessuna seconda copia di PyTorch sul disco).
set "UVROOT=%~dp0data\uv"
set "UV_DATA_DIR=%UVROOT%"
set "UV_PYTHON_INSTALL_DIR=%UVROOT%\python"
set "UV_PYTHON_BIN_DIR=%UVROOT%\bin"
set "UV_CACHE_DIR=%UVROOT%\cache"
set "UV_PROJECT_ENVIRONMENT=%~dp0.venv"
set "UV_PYTHON_PREFERENCE=only-managed"
set "UV_LINK_MODE=hardlink"
rem Connessioni lente: timeout lungo, pochi download in parallelo, piu' tentativi per ogni file.
set "UV_HTTP_TIMEOUT=600"
set "UV_CONCURRENT_DOWNLOADS=3"
set "UV_HTTP_RETRIES=8"
set "FROZEN="
if exist "%~dp0uv.lock" set "FROZEN=--frozen"

rem Fino a 4 tentativi: ogni volta riparte dai pacchetti gia' scaricati.
set "TRY=0"
:retry
set /a TRY+=1
"%~dp0bin\uv.exe" sync %FROZEN% --no-dev --python 3.11
if not errorlevel 1 goto ok
if %TRY% LSS 4 (
  echo.
  echo  Tentativo %TRY% di 4 non riuscito, riprovo tra 10 secondi.
  echo.
  timeout /t 10 /nobreak >nul
  goto retry
)

echo.
echo  Preparazione non riuscita.
echo  Se l'errore parla di "spazio su disco insufficiente" libera almeno 15 GB sul disco di installazione.
echo  Se parla di timeout o di rete, riprova piu' tardi o con una connessione migliore.
echo  Poi riprova da menu Start, "Audyum - ripara installazione": riparte dai file gia' scaricati.
echo.
pause
exit /b 1

:ok
rem A fine lavoro la cache non serve piu' e occupa diversi GB.
"%~dp0bin\uv.exe" cache clean >nul 2>&1
exit /b 0
