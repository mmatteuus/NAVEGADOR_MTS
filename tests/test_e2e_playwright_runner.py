"""Validador Pytest E2E: Executa suíte com Chromium Real e Playwright."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import pytest


def test_e2e_real_multisession_playwright() -> None:
    """Executa a suíte de testes E2E com Chromium real e validação de 5 cenários.

    Verifica empiricamente:
    1. Gravação de autenticação e localStorage no Agente A.
    2. Isolamento físico estrito de cookies e storage para o Agente B.
    3. Segregação de listagem de abas.
    4. Bloqueio adversarial de acesso à aba de A por B (TAB_ACCESS_DENIED).
    5. Disparos concorrentes simultâneos sem interferência de sessões.
    """
    root_dir = Path(__file__).resolve().parents[1]
    script_path = root_dir / "tests" / "e2e_real" / "test_e2e_real_multisession.mjs"

    env = os.environ.copy()
    if "APPDATA" in env and "NODE_PATH" not in env:
        global_npm = Path(env["APPDATA"]) / "npm" / "node_modules"
        if global_npm.exists():
            env["NODE_PATH"] = str(global_npm)

    result = subprocess.run(
        ["node", str(script_path)],
        cwd=str(root_dir),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )

    if result.returncode != 0:
        pytest.fail(
            f"Falha na execução do teste E2E Real Playwright (exit={result.returncode}):\n"
            f"--- STDOUT ---\n{result.stdout}\n"
            f"--- STDERR ---\n{result.stderr}"
        )

    assert result.stdout is not None
    assert "SUCESSO TOTAL! 5 CENÁRIOS E2E REAL APROVADOS COM LOUVOR!" in result.stdout
