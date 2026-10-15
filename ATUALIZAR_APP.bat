@echo off
setlocal
cd /d "%~dp0"
title BROWSER MTS - Atualizar
set "INSTALLER=%~dp0dist_installer\NAVEGADOR_MTS_Instalador_v2.1.1.exe"
if not exist "%INSTALLER%" (
  echo [ERRO] Instalador nao encontrado: "%INSTALLER%"
  echo Execute COMPILAR_INSTALADOR.bat antes de atualizar.
  pause
  exit /b 1
)
echo Instalando versao 2.1.1 sobre a instalacao existente...
start /wait "" "%INSTALLER%" /CLOSEAPPLICATIONS /FORCECLOSEAPPLICATIONS
if errorlevel 1 (
  echo [ERRO] O instalador nao concluiu com sucesso.
  pause
  exit /b 1
)
set "APP_EXE=%LOCALAPPDATA%\Programs\Navegador MTS\NAVEGADOR_MTS.exe"
if not exist "%APP_EXE%" (
  echo [ERRO] Executavel nao encontrado apos instalacao: "%APP_EXE%"
  pause
  exit /b 1
)
start "" "%APP_EXE%"
echo [OK] Instalacao atualizada.
pause
