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
& $Python -m pytest -q tests/test_mcp_protocol.py tests/test_mcp_http.py tests/test_mcp_http_e2e.py tests/test_mcp_ws_bridge.py tests/test_mcp_computer_adapter.py tests/test_tunnel_service.py tests/test_updater.py tests/test_updater_regression.py
if ($LASTEXITCODE -ne 0) { throw "Testes Python falharam; compilação suspensa." }

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js não encontrado; teste da extensão não executado."
}
& node tests/test_extension_adversarial.mjs
if ($LASTEXITCODE -ne 0) { throw "Teste da extensão falhou." }

Write-Host "[OK] Testes de contrato concluídos." -ForegroundColor Green
if ($SemCompilar) { return }

& $Python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "PyInstaller indisponível." }
& $Python generate_icon.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar ícone." }
& $Python build_exe.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar executáveis." }
& $Python build_installer.py
if ($LASTEXITCODE -ne 0) { throw "Inno Setup não encontrado ou compilação falhou." }
$Installer = Join-Path $PSScriptRoot "dist_installer\NAVEGADOR_MTS_Instalador_v2.1.3.exe"
if (-not (Test-Path $Installer)) { throw "Arquivo instalador ausente." }
Write-Host "[OK] Instalador de TESTE: $Installer" -ForegroundColor Green
Write-Host "Instalação não executada automaticamente; backup e rollback ficam sob seu controle."
