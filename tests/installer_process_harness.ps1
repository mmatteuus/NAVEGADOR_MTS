param([ValidateSet('scope','respawn','inaccessible','fresh')][string]$Scenario)

$ErrorActionPreference = 'Stop'
$global:Fake = @()
$global:Closed = @()
$root = 'C:\Scratch\Navegador MTS'
$owned = "$root\NAVEGADOR_MTS.exe"
$child = "$root\tunnel-client.exe"
$external = 'C:\Scratch\Navegador MTS-copy\NAVEGADOR_MTS.exe'
$protected = [pscustomobject]@{ ProcessId = 9999; ParentProcessId = 1; ExecutablePath = $external; CreationDate = '20261016100001.000000-180' }
$global:Fake += [pscustomobject]@{ ProcessId = 1001; ParentProcessId = 1; ExecutablePath = $owned; CreationDate = '20261016100000.000000-180' }
$global:Fake += $protected
if ($Scenario -eq 'inaccessible') { $global:Fake += [pscustomobject]@{ ProcessId = 1002; ParentProcessId = 1001; ExecutablePath = $child; CreationDate = '20261016100002.000000-180' } }
$script:SleepCount = 0

function Test-Path { param($LiteralPath, $PathType) return $true }
function Get-CimInstance {
    param($ClassName, $Filter)
    if ($Filter) {
        $wantedPid = [int]($Filter -replace '\D', '')
        return @($global:Fake | Where-Object ProcessId -eq $wantedPid)
    }
    return @($global:Fake)
}
function Get-Process {
    param($Id, $ErrorAction)
    if ($Scenario -eq 'inaccessible') { throw 'simulated access denied' }
    $global:CurrentCloseId = $Id
    $process = [pscustomobject]@{ MainWindowHandle = $(if ($Id -eq 1001) { 1 } else { 0 }) }
    $process | Add-Member ScriptMethod CloseMainWindow {
        $closeId = $global:CurrentCloseId
        $global:Closed += $closeId
        $global:Fake = @($global:Fake | Where-Object ProcessId -ne $closeId)
        if ($Scenario -eq 'respawn' -and $closeId -eq 1001) {
            $global:Fake += [pscustomobject]@{ ProcessId = 1003; ParentProcessId = 1001; ExecutablePath = $child; CreationDate = '20261016100003.000000-180' }
        }
    }
    return $process
}
function Stop-Process {
    param($Id, [switch]$Force, $ErrorAction)
    if ($Scenario -eq 'inaccessible') { throw 'simulated access denied' }
    Write-Output "STOP:$Id"
    $global:Fake = @($global:Fake | Where-Object ProcessId -ne $Id)
}
function Start-Sleep { param($Milliseconds) }

if ($Scenario -eq 'fresh') { function Test-Path { return $false } }
& (Join-Path $PSScriptRoot '..\installer\close_owned_processes.ps1') -InstallDir $root
foreach ($closedId in $global:Closed) { Write-Output "CLOSED:$closedId" }
Write-Output 'HARNESS:completed'
