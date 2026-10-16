"""Regressão do encerramento restrito à pasta instalada."""

from pathlib import Path


def test_installer_uses_scoped_process_helper():
    """O helper deve revalidar caminho e não usar encerramento global."""
    script = Path("installer/close_owned_processes.ps1").read_text(encoding="utf-8")
    setup = Path("installer.iss").read_text(encoding="utf-8")
    assert "Get-CimInstance Win32_Process" in script
    assert "Join-Path $root 'tunnel-client.exe'" in script
    assert "mcp_stdio\\NAVEGADOR_MTS_MCP.exe" in script
    assert "Stop-Process -Id ([int]$current.ProcessId) -Force" in script
    assert "taskkill" not in script.lower()
    assert "PrepareToInstall" in setup
