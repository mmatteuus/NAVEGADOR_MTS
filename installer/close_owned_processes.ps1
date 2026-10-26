param([Parameter(Mandatory=$true)][string]$InstallDir)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallDir).TrimEnd('\')
$paths = @(
    (Join-Path $root 'NAVEGADOR_MTS.exe'),
    (Join-Path $root 'tunnel-client.exe'),
    (Join-Path $root 'cloudflared.exe'),
    (Join-Path $root 'mcp_stdio\NAVEGADOR_MTS_MCP.exe'))
if ($root -match '^[A-Za-z]:\\?$') { exit 1 }
if (!(Test-Path -LiteralPath $root -PathType Container) -or !(Test-Path -LiteralPath $paths[0] -PathType Leaf)) { exit 0 }
function Get-OwnedProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $currentPath = $_.ExecutablePath
        $currentPath -and (@($paths | ForEach-Object { $_.Equals($currentPath, [StringComparison]::OrdinalIgnoreCase) }) -contains $true)
    }
}
function Stop-OwnedProcess([object]$item, [bool]$Force) {
    $current = Get-CimInstance Win32_Process -Filter "ProcessId = $($item.ProcessId)"
    if (!$current) { return }
    $currentPath = $current.ExecutablePath
    if ($currentPath -and $current.CreationDate -eq $item.CreationDate -and
        $currentPath.Equals($item.ExecutablePath, [StringComparison]::OrdinalIgnoreCase)) {
        try {
            if ($Force) { Stop-Process -Id ([int]$current.ProcessId) -Force -ErrorAction Stop; return }
            $process = Get-Process -Id ([int]$current.ProcessId) -ErrorAction Stop
            if ($process.MainWindowHandle -ne 0) { [void]$process.CloseMainWindow() }
        } catch {
            $stillAlive = Get-CimInstance Win32_Process -Filter "ProcessId = $($item.ProcessId)"
            if ($stillAlive) { throw }
        }
    }
}
Get-OwnedProcesses | Where-Object { $_.ExecutablePath.Equals($paths[0], [StringComparison]::OrdinalIgnoreCase) } |
    ForEach-Object { Stop-OwnedProcess $_ $false }
$deadline = (Get-Date).AddSeconds(8)
do {
    $alive = @(Get-OwnedProcesses | Where-Object { $_.ExecutablePath.Equals($paths[0], [StringComparison]::OrdinalIgnoreCase) })
    if (!$alive) { break }
    Start-Sleep -Milliseconds 250
} while ((Get-Date) -lt $deadline)

if (@(Get-OwnedProcesses | Where-Object { $_.ExecutablePath.Equals($paths[0], [StringComparison]::OrdinalIgnoreCase) })) {
    Get-OwnedProcesses | Where-Object { $_.ExecutablePath.Equals($paths[0], [StringComparison]::OrdinalIgnoreCase) } |
        ForEach-Object { Stop-OwnedProcess $_ $true }
}
$deadline = (Get-Date).AddSeconds(3)
do {
    if (!(Get-OwnedProcesses | Where-Object { $_.ExecutablePath.Equals($paths[0], [StringComparison]::OrdinalIgnoreCase) })) { break }
    Start-Sleep -Milliseconds 250
} while ((Get-Date) -lt $deadline)
if (@(Get-OwnedProcesses | Where-Object { $_.ExecutablePath.Equals($paths[0], [StringComparison]::OrdinalIgnoreCase) })) { exit 1 }
$deadline = (Get-Date).AddSeconds(5)
do {
    $helpers = @(Get-OwnedProcesses | Where-Object { !$_.ExecutablePath.Equals($paths[0], [StringComparison]::OrdinalIgnoreCase) })
    if (!$helpers) { break }
    $helpers | ForEach-Object { Stop-OwnedProcess $_ $true }
    Start-Sleep -Milliseconds 250
} while ((Get-Date) -lt $deadline)
if (@(Get-OwnedProcesses).Count -eq 0) { exit 0 }
exit 1
