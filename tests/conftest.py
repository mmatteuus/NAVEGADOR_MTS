"""Configurações e Fixtures Globais da Suíte de Testes do BROWSER MTS.

Inclusão do diretório raiz no PYTHONPATH.
Sentinela de isolamento estrito da instância de produção.
Gerenciamento de portas dinâmicas e limpeza de processos filhos nos testes.

"""
from __future__ import annotations

import os
import socket
import sys
from typing import Generator, List
import psutil
import pytest

# Garante que a raiz do projeto esteja no sys.path para importação de src.*
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.computer.safety_gate import safety_gate  # noqa: E402

PROD_PIDS = [17892, 8928, 6548, 6052]


@pytest.fixture(scope="session", autouse=True)
def guard_production_instance() -> Generator[None, None, None]:
    """Sentinela que assegura que nenhum PID da produção seja alterado ou morto."""
    active_before = [pid for pid in PROD_PIDS if psutil.pid_exists(pid)]
    yield
    active_after = [pid for pid in PROD_PIDS if psutil.pid_exists(pid)]
    # Se algum PID de produção estava vivo antes do teste, deve continuar vivo
    for pid in active_before:
        assert pid in active_after, (
            f"VIOLAÇÃO CRÍTICA DE PRODUÇÃO: O PID {pid} da produção foi interrompido!"
        )


@pytest.fixture
def reset_safety_gate() -> Generator[None, None, None]:
    """Restaura o estado do SafetyGate para desautorizado antes e após cada teste."""
    safety_gate.revoke("Preparação do teste")
    safety_gate.reset_kill_switch()
    yield
    safety_gate.revoke("Limpeza pós-teste")
    safety_gate.reset_kill_switch()


@pytest.fixture
def dynamic_port() -> int:
    """Aloca e retorna uma porta TCP livre e isolada para testes de rede."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = s.getsockname()[1]
    return port


@pytest.fixture
def process_cleanup_tracker() -> Generator[List[psutil.Process], None, None]:
    """Rastreia e finaliza obrigatoriamente qualquer processo filho criado nos testes."""
    tracked_procs: List[psutil.Process] = []
    yield tracked_procs
    for proc in tracked_procs:
        try:
            if proc.is_running():
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass