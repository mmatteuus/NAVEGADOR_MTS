@echo off
chcp 65001 >nul
echo ========================================================
echo     COMPILADOR DO INSTALADOR UNICO - NAVEGADOR MTS
echo ========================================================
echo.
echo [1/3] Gerando icones e assets visuais...
.\.venv\Scripts\python.exe generate_icon.py
if %ERRORLEVEL% neq 0 (
    echo Erro ao gerar icones.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Compilando executavel standalone com PyInstaller...
.\.venv\Scripts\python.exe build_exe.py
if %ERRORLEVEL% neq 0 (
    echo Erro no PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Gerando instalador executavel oficial com Inno Setup...
.\.venv\Scripts\python.exe build_installer.py
if %ERRORLEVEL% neq 0 (
    echo Erro no Inno Setup.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo     INSTALADOR GERADO COM SUCESSO!
echo     Local: dist_installer\NAVEGADOR_MTS_Instalador_v2.1.1.exe
echo ========================================================
echo.
explorer.exe /select,"dist_installer\NAVEGADOR_MTS_Instalador_v2.0.exe"
pause
