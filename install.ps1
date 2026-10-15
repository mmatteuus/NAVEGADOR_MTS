<#
.SYNOPSIS
    Script de Instalacao e Provisionamento Autonomo do BROWSER MTS no Windows 11.

.DESCRIPTION
    Configura o ambiente do BROWSER MTS em uma maquina Windows limpa:
    - Valida o interpretador Python (>= 3.10)
    - Cria e inicializa o ambiente virtual (.venv)
    - Instala todas as dependencias declaradas no requirements.txt
    - Cria o atalho oficial no Menu Iniciar do Windows com suporte a execucao minimizada
    - Opcionalmente inicia a aplicacao apos o provisionamento

.PARAMETER Minimized
    Configura o atalho para iniciar o aplicativo diretamente minimizado na bandeja do sistema.

.PARAMETER CreateShortcut
    Cria ou atualiza o atalho do aplicativo no Menu Iniciar.

.PARAMETER StartNow
    Inicia o aplicativo imediatamente apos a conclusao da instalacao.

.PARAMETER SkipVenv
    Pula a criacao do ambiente virtual e utiliza os pacotes do Python global.

.EXAMPLE
    .\install.ps1
    Instalacao padrao com ambiente virtual e atalho no Menu Iniciar.

.EXAMPLE
    .\install.ps1 -Minimized -StartNow
    Instala, cria o atalho para inicio na bandeja e inicia o aplicativo imediatamente.
#>

[CmdletBinding()]
param (
    [switch]$Minimized,
    [switch]$CreateShortcut,
    [switch]$StartNow,
    [switch]$SkipVenv,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Info([string]$Message) {
    if (-not $Quiet) {
        Write-Host "[INFO] $Message" -ForegroundColor Cyan
    }
}

function Write-Success([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-WarningMessage([string]$Message) {
    Write-Host "[AVISO] $Message" -ForegroundColor Yellow
}

function Write-ErrorMessage([string]$Message) {
    Write-Host "[ERRO] $Message" -ForegroundColor Red
}

Write-Host "==============================================================================" -ForegroundColor DarkCyan
Write-Host "               BROWSER MTS -- Provisionamento para Windows 11                 " -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor DarkCyan
Write-Host ""

# 1. Validacao do Python no sistema
Write-Info "Verificando interpretador Python..."
$PythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    $PythonCmd = Get-Command "py" -ErrorAction SilentlyContinue
}

if (-not $PythonCmd) {
    Write-ErrorMessage "Interpretador Python nao encontrado no PATH do sistema!"
    Write-Host "Por favor, instale o Python 3.10 ou superior a partir de https://python.org" -ForegroundColor White
    exit 1
}

$PythonVersionOutput = & $PythonCmd.Source --version 2>&1
Write-Success "Python detectado: $PythonVersionOutput ($($PythonCmd.Source))"

# 2. Configuracao do Ambiente Virtual (.venv)
$VenvDir = Join-Path $ScriptDir ".venv"
$PythonExe = $PythonCmd.Source
$PythonwExe = Join-Path (Split-Path -Parent $PythonCmd.Source) "pythonw.exe"

if (-not $SkipVenv) {
    Write-Info "Configurando ambiente virtual (.venv)..."
    if (-not (Test-Path $VenvDir)) {
        & $PythonCmd.Source -m venv $VenvDir
        if ($LASTEXITCODE -eq 0 -and (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
            Write-Success "Ambiente virtual criado em: $VenvDir"
        } else {
            Write-WarningMessage "Falha ao criar .venv. Prosseguindo com Python global."
        }
    } else {
        Write-Success "Ambiente virtual existente detectado: $VenvDir"
    }

    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    $VenvPythonw = Join-Path $VenvDir "Scripts\pythonw.exe"
    if (Test-Path $VenvPython) {
        $PythonExe = $VenvPython
        $PythonwExe = $VenvPythonw
    }
}

# 3. Instalacao das dependencias
$ReqFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $ReqFile) {
    Write-Info "Instalando dependencias de $ReqFile..."
    & $PythonExe -m pip install --upgrade pip --quiet
    & $PythonExe -m pip install -r $ReqFile --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Todas as dependencias foram instaladas com sucesso."
    } else {
        Write-WarningMessage "Instalacao de pacotes concluida com advertencias."
    }
} else {
    Write-WarningMessage "requirements.txt nao encontrado na raiz."
}

# 4. Criacao do Atalho no Menu Iniciar (padrao: ativado)
$ShouldCreate = $true
if ($PSBoundParameters.ContainsKey('CreateShortcut')) {
    $ShouldCreate = $CreateShortcut.IsPresent
}

if ($ShouldCreate) {
    Write-Info "Criando atalho no Menu Iniciar do Windows..."
    $ProgramsFolder = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs")
    if (-not (Test-Path $ProgramsFolder)) {
        New-Item -ItemType Directory -Path $ProgramsFolder -Force | Out-Null
    }

    $ShortcutPath = Join-Path $ProgramsFolder "BROWSER MTS.lnk"
    $TargetScript = Join-Path $ScriptDir "entrypoint.py"
    $IconPath = Join-Path $ScriptDir "docs\screenshots\system_tray_icon.png"

    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)

    if (Test-Path $PythonwExe) {
        $Shortcut.TargetPath = $PythonwExe
    } else {
        $Shortcut.TargetPath = $PythonExe
    }

    $ArgStr = '"{0}"' -f $TargetScript
    if ($Minimized) {
        $ArgStr = $ArgStr + " --minimized"
    }
    $Shortcut.Arguments = $ArgStr
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.Description = "BROWSER MTS - Automacao de Navegador e Computador para IA (Windows 11)"

    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = $IconPath
    }

    $Shortcut.Save()
    Write-Success "Atalho criado com sucesso em: $ShortcutPath"
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "             INSTALACAO DO BROWSER MTS CONCLUIDA COM EXITO!                   " -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "Diretorio: $ScriptDir" -ForegroundColor Gray
Write-Host "Atalho no Menu Iniciar: BROWSER MTS" -ForegroundColor Gray
Write-Host "Comando manual: $PythonExe src\app.py" -ForegroundColor Gray
Write-Host ""

if ($StartNow) {
    Write-Info "Iniciando BROWSER MTS agora..."
    $TargetScript = Join-Path $ScriptDir "entrypoint.py"
    Start-Process -FilePath $PythonwExe -ArgumentList ('"{0}"' -f $TargetScript) -WorkingDirectory $ScriptDir
    Write-Success "Aplicativo disparado em segundo plano."
}
