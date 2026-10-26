@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: BROWSER MTS -- Instalador e Configurador Autonomo para Windows
:: ============================================================================

echo ==============================================================================
echo               BROWSER MTS -- Instalador e Configurador Autonomo
echo ==============================================================================
echo.

:: 1. Verificar instalacao do Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Python nao foi encontrado no sistema ou nao esta no PATH do Windows!
    echo Por favor, instale o Python 3.10 ou superior a partir de: https://python.org
    echo Certifique-se de marcar a opcao para adicionar Python ao PATH.
    echo.
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python detectado: %PYTHON_VERSION%
echo.

:: Determinar o diretorio raiz do projeto
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: 2. Configurar o Ambiente Virtual (.venv)
echo [1/3] Configurando ambiente virtual Python (.venv)...
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "PYTHONW_EXE=%PROJECT_DIR%\.venv\Scripts\pythonw.exe"

if not exist "%VENV_DIR%" (
    echo Criando ambiente virtual isolado...
    python -m venv "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo [AVISO] Nao foi possivel criar .venv. Utilizando interpretador global...
        set "PYTHON_EXE=python"
        set "PYTHONW_EXE=pythonw"
    ) else (
        echo [OK] Ambiente virtual criado com sucesso em "%VENV_DIR%".
    )
) else (
    echo [OK] Ambiente virtual existente detectado em "%VENV_DIR%".
)

:: 3. Instalar Dependencias do requirements.txt
echo.
echo [2/3] Instalando dependencias de requirements.txt...
if exist "%PROJECT_DIR%\requirements.txt" (
    "%PYTHON_EXE%" -m pip install --upgrade pip --quiet
    "%PYTHON_EXE%" -m pip install -r "%PROJECT_DIR%\requirements.txt" --quiet
    if %ERRORLEVEL% neq 0 (
        echo [AVISO] Instalacao parcial de dependencias. Executando em modo de compatibilidade.
    ) else (
        echo [OK] Todas as dependencias foram instaladas com sucesso.
    )
) else (
    echo [AVISO] requirements.txt nao encontrado. Pulando etapa de pacotes.
)

:: 4. Criar Atalho Oficial no Menu Iniciar
echo.
echo [3/3] Criando atalho no Menu Iniciar do Windows...
set "SHORTCUT_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "SHORTCUT_PATH=%SHORTCUT_DIR%\BROWSER MTS.lnk"
set "TARGET_APP=%PROJECT_DIR%\entrypoint.py"
set "ICON_PATH=%PROJECT_DIR%\docs\screenshots\system_tray_icon.png"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%PYTHONW_EXE%'; $s.Arguments = '\"%TARGET_APP%\"'; $s.WorkingDirectory = '%PROJECT_DIR%'; $s.Description = 'BROWSER MTS -- Automacao de Navegador e Computador para IA'; if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%'; } $s.Save(); Write-Output '[OK] Atalho criado em: %SHORTCUT_PATH%';"

echo.
echo ==============================================================================
echo                   INSTALACAO CONCLUIDA COM SUCESSO!
echo ==============================================================================
echo O BROWSER MTS esta pronto para uso no Windows.
echo Atalho criado no Menu Iniciar: "BROWSER MTS"
echo Local do projeto: "%PROJECT_DIR%"
echo.

if "%1"=="/silent" goto :fim
if "%1"=="/start" (
    echo Iniciando BROWSER MTS...
    start "" "%PYTHONW_EXE%" "%TARGET_APP%"
    goto :fim
)

echo Deseja iniciar o BROWSER MTS agora?
set "START_NOW=S"
set /p START_NOW="[S/N] (Padrao: S): "
if /i "%START_NOW%"=="S" (
    echo Iniciando BROWSER MTS...
    start "" "%PYTHONW_EXE%" "%TARGET_APP%"
)

:fim
echo Instalacao finalizada.
