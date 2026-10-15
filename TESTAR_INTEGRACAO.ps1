<#
.SYNOPSIS
Smoke test local, não destrutivo, do NAVEGADOR MTS no Windows.
.EXAMPLE
.\TESTAR_INTEGRACAO.ps1 -StartApp
#>
[CmdletBinding()]
param([switch]$StartApp)

$ErrorActionPreference = "Stop"
$BaseUrl = "http://127.0.0.1:3457"
$Exe = Join-Path $env:LOCALAPPDATA "Programs\Navegador MTS\NAVEGADOR_MTS.exe"

function Invoke-Mcp([string]$Method, [object]$Params, [int]$Id) {
    $Request = @{ jsonrpc = "2.0"; id = $Id; method = $Method; params = $Params }
    $Body = ConvertTo-Json -InputObject $Request -Depth 12 -Compress
    return Invoke-RestMethod -Method Post -Uri "$BaseUrl/mcp" -Body $Body -ContentType "application/json" -TimeoutSec 6
}
function Test-Health {
    try {
        $Health = Invoke-RestMethod -Uri "$BaseUrl/healthz" -TimeoutSec 2
        return ($Health.status -eq "ok" -and $Health.service -eq "browser-mcp-mts")
    } catch { return $false }
}

if (-not (Test-Health) -and $StartApp) {
    if (-not (Test-Path $Exe)) {
        throw "NAVEGADOR_MTS.exe não encontrado: $Exe"
    }
    Start-Process -FilePath $Exe
    for ($i = 0; $i -lt 15 -and -not (Test-Health); $i++) {
        Start-Sleep -Milliseconds 500
    }
}
if (-not (Test-Health)) {
    throw "Servidor HTTP local indisponível em $BaseUrl. Abra o NAVEGADOR MTS."
}
Write-Host "[OK] Health MCP local (porta 3457)." -ForegroundColor Green

$Init = Invoke-Mcp "initialize" @{ protocolVersion = "2025-06-18"; capabilities = @{}; clientInfo = @{name="smoke-test";version="1"} } 1
if ($Init.result.serverInfo.name -ne "browser-mcp-mts") {
    throw "O servidor encontrado não é o NAVEGADOR MTS."
}
Write-Host "[OK] MCP initialize v$($Init.result.serverInfo.version)." -ForegroundColor Green

$Tools = Invoke-Mcp "tools/list" @{} 2
$Names = @($Tools.result.tools | ForEach-Object { $_.name })
if (-not ($Names -contains "browser_navigate") -or -not ($Names -contains "computer_get_status")) {
    throw "Ferramentas MCP essenciais não encontradas."
}
Write-Host "[OK] $($Names.Count) ferramentas registradas." -ForegroundColor Green

$Gate = Invoke-Mcp "tools/call" @{ name="computer_get_status"; arguments=@{} } 3
$Status = $Gate.result.content[0].text | ConvertFrom-Json
Write-Host "[OK] SafetyGate: autorizado=$($Status.authorized); emergência=$($Status.killSwitchActive)."
Write-Host "Nenhuma ação de mouse, teclado ou screenshot foi executada."
Write-Host "[PENDENTE] Confirmar tunnel-client /readyz e descobrir ferramenta no ChatGPT."
