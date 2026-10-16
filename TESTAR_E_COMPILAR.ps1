<#
.SYNOPSIS
Testa o código no Windows e compila um instalador sem instalá-lo.
.EXAMPLE
.\TESTAR_E_COMPILAR.ps1
#>
[CmdletBinding()]
param([switch]$SemCompilar)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv ".venv"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv ".venv"
    } else {
        throw "Python 3.10+ não encontrado. Instale Python e tente novamente."
    }
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar .venv." }
}
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar pip." }
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências." }

& $Python -m compileall -q src entrypoint.py stdio_entrypoint.py
if ($LASTEXITCODE -ne 0) { throw "Falha na sintaxe Python." }
& $Python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "PyInstaller indisponível." }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Testes Python falharam; compilação suspensa." }

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js não encontrado; teste da extensão não executado."
}
& node tests/test_extension_adversarial.mjs
if ($LASTEXITCODE -ne 0) { throw "Teste da extensão falhou." }

Write-Host "[OK] Testes de contrato concluídos." -ForegroundColor Green
if ($SemCompilar) { return }

& $Python generate_icon.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar ícone." }
& $Python build_exe.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar executáveis." }
& $Python build_installer.py
if ($LASTEXITCODE -ne 0) { throw "Inno Setup não encontrado ou compilação falhou." }
$Version = (& $Python -c "from src.version import APP_VERSION; print(APP_VERSION)").Trim()
if ([string]::IsNullOrWhiteSpace($Version)) { throw "Fonte canonica de versão vazia." }
$Installer = Join-Path $PSScriptRoot "dist_installer\NAVEGADOR_MTS_Instalador_v$Version.exe"
if (-not (Test-Path $Installer)) { throw "Arquivo instalador ausente." }
Write-Host "[OK] Instalador de TESTE: $Installer" -ForegroundColor Green
Write-Host "Instalação não executada automaticamente; backup e rollback ficam sob seu controle."
