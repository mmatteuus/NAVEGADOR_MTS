@echo off
chcp 65001 >nul
echo ========================================================
echo     COMPILADOR DO INSTALADOR UNICO - NAVEGADOR MTS
echo ========================================================
echo.
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" --version >nul 2>&1
if %ERRORLEVEL% neq 0 exit /b 1
"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Erro: PyInstaller nao esta instalado no ambiente selecionado.
    exit /b 1
)
for /f "delims=" %%V in ('"%PYTHON%" -c "from src.version import APP_VERSION; print(APP_VERSION)" 2^>nul') do set "MTS_VERSION=%%V"
if not defined MTS_VERSION exit /b 1
echo [1/3] Gerando icones e assets visuais...
"%PYTHON%" generate_icon.py
if %ERRORLEVEL% neq 0 (
    echo Erro ao gerar icones.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Compilando executavel standalone com PyInstaller...
"%PYTHON%" build_exe.py
if %ERRORLEVEL% neq 0 (
    echo Erro no PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Gerando instalador executavel oficial com Inno Setup...
"%PYTHON%" build_installer.py
if %ERRORLEVEL% neq 0 (
    echo Erro no Inno Setup.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo     INSTALADOR GERADO COM SUCESSO!
echo     Local: dist_installer\NAVEGADOR_MTS_Instalador_v%MTS_VERSION%.exe
echo ========================================================
echo.
explorer.exe /select,"dist_installer\NAVEGADOR_MTS_Instalador_v%MTS_VERSION%.exe"
pause
