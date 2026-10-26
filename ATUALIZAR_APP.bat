@echo off
setlocal
cd /d "%~dp0"
title BROWSER MTS - Atualizar
for /f "delims=" %%V in ('python -c "from src.version import APP_VERSION; print(APP_VERSION)" 2^>nul') do set "MTS_VERSION=%%V"
if not defined MTS_VERSION exit /b 1
set "INSTALLER=%~dp0dist_installer\NAVEGADOR_MTS_Instalador_v%MTS_VERSION%.exe"
if not exist "%INSTALLER%" (
  echo [ERRO] Instalador nao encontrado: "%INSTALLER%"
  echo Execute COMPILAR_INSTALADOR.bat antes de atualizar.
  pause
  exit /b 1
)
echo Instalando versao %MTS_VERSION% sobre a instalacao existente...
start /wait "" "%INSTALLER%" /CLOSEAPPLICATIONS /FORCECLOSEAPPLICATIONS
if errorlevel 1 (
  echo [ERRO] O instalador nao concluiu com sucesso.
  pause
  exit /b 1
)
set "APP_EXE=%LOCALAPPDATA%\Programs\NAVEGADOR MTS\NAVEGADOR_MTS.exe"
if not exist "%APP_EXE%" (
  echo [ERRO] Executavel nao encontrado apos instalacao: "%APP_EXE%"
  pause
  exit /b 1
)
tasklist /FI "IMAGENAME eq NAVEGADOR_MTS.exe" 2>nul | find /I "NAVEGADOR_MTS.exe" >nul
if errorlevel 1 (
  start "" "%APP_EXE%"
)
echo [OK] Instalacao atualizada.
pause
