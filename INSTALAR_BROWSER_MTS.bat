@echo off
setlocal EnableDelayedExpansion
title BROWSER MTS -- Instalador 1-Clique

echo ==============================================================================
echo               BROWSER MTS -- Instalador 1-Clique para Windows
echo ==============================================================================
echo.
echo Este instalador configura tudo automaticamente no seu computador:
echo   - Cria o ambiente seguro local (armazenamento 100%% no seu computador)
echo   - Instala as dependencias necessarias
echo   - Cria os atalhos no Menu Iniciar e na Area de Trabalho
echo   - Inicia o aplicativo moderno com visual nativo do Windows
echo.
echo ==============================================================================
echo.

:: Executa o setup interno
call "%~dp0setup.bat" /start

:: Cria atalho na Area de Trabalho tambem para maxima facilidade
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "DESKTOP_SHORTCUT=%DESKTOP_DIR%\BROWSER MTS.lnk"
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYTHONW_EXE=%PROJECT_DIR%\.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW_EXE%" set "PYTHONW_EXE=pythonw"
set "TARGET_APP=%PROJECT_DIR%\entrypoint.py"
set "ICON_PATH=%PROJECT_DIR%\docs\screenshots\system_tray_icon.png"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP_SHORTCUT%'); $s.TargetPath = '%PYTHONW_EXE%'; $s.Arguments = '\"%TARGET_APP%\"'; $s.WorkingDirectory = '%PROJECT_DIR%'; $s.Description = 'BROWSER MTS -- Automacao de Navegador e Computador para IA'; if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%'; } $s.Save();" 2>nul

echo.
echo [SUCESSO] Atalhos criados no Menu Iniciar e na sua Area de Trabalho!
echo.

