"""Ensaios controlados do helper de processos do instalador."""

from pathlib import Path
import subprocess


HARNESS = Path("tests/installer_process_harness.ps1")


def run_harness(scenario: str) -> subprocess.CompletedProcess[str]:
    """Executa somente o harness com processos CIM/Stop-Process simulados."""
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(HARNESS), scenario],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_scope_ignores_prefix_collision_and_protected_pid():
    """Somente caminhos exatamente iguais podem ser selecionados."""
    result = run_harness("scope")
    assert result.returncode == 0
    assert "HARNESS:completed" in result.stdout
    assert "STOP:9999" not in result.stdout


def test_respawn_is_rediscovered_before_success():
    """Um processo filho reaparecido durante a espera deve ser fechado."""
    result = run_harness("respawn")
    assert result.returncode == 0
    assert "STOP:1003" in result.stdout


def test_inaccessible_process_fails_closed():
    """Falha de encerramento deve impedir o Setup de continuar."""
    result = run_harness("inaccessible")
    assert result.returncode != 0


def test_fresh_install_without_processes_is_noop():
    """Uma instalação nova não precisa encerrar processos."""
    result = run_harness("fresh")
    assert result.returncode == 0
