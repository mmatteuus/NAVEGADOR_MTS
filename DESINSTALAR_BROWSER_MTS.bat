@echo off
chcp 65001 >nul
echo ========================================================
echo       DESINSTALADOR OFICIAL DO BROWSER MTS
echo ========================================================
echo.

echo [1/4] Encerrando processos em segundo plano do aplicativo...
taskkill /F /IM BROWSER_MTS.exe >nul 2>&1

echo.
echo [2/4] Removendo inicializacao automatica com Windows...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "BrowserMTS" /f >nul 2>&1

echo.
echo [3/4] Removendo atalhos da Area de Trabalho e Menu Iniciar...
del /F /Q "%USERPROFILE%\Desktop\BROWSER MTS.lnk" >nul 2>&1
del /F /Q "%USERPROFILE%\Desktop\Extensao Chrome BROWSER MTS.lnk" >nul 2>&1
del /F /Q "%PUBLIC%\Desktop\BROWSER MTS.lnk" >nul 2>&1
rmdir /S /Q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\BROWSER MTS" >nul 2>&1
rmdir /S /Q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\BROWSER MTS 2.0" >nul 2>&1

echo.
echo [4/4] Executando desinstalador oficial...
if exist "%APPDATA%\Programs\BROWSER MTS\unins000.exe" (
    echo Iniciando desinstalador do sistema...
    start "" /wait "%APPDATA%\Programs\BROWSER MTS\unins000.exe" /SILENT
    rmdir /S /Q "%APPDATA%\Programs\BROWSER MTS" >nul 2>&1
)

if exist "%LOCALAPPDATA%\Programs\BROWSER MTS\unins000.exe" (
    echo Iniciando desinstalador do sistema...
    start "" /wait "%LOCALAPPDATA%\Programs\BROWSER MTS\unins000.exe" /SILENT
    rmdir /S /Q "%LOCALAPPDATA%\Programs\BROWSER MTS" >nul 2>&1
)

echo.
echo ========================================================
echo       BROWSER MTS DESINSTALADO COM SUCESSO!
echo ========================================================
echo.
pause

