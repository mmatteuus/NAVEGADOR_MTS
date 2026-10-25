"""Testes unitários e de integração para o ProcessSupervisor (src/core/supervisor.py).

Verifica o gerenciamento de ciclo de vida de processos, encerramento em árvore via psutil,
fechamento de fluxos Popen e resiliência a exceções de processo inexistente/negado.
"""

from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock
import psutil
import pytest

from src.core.supervisor import ProcessSupervisor


def test_supervisor_start_is_alive_and_terminate():
    """Testa ciclo básico: inicialização, verificação de vida e encerramento em árvore."""
    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    supervisor = ProcessSupervisor(command=cmd, name="test_proc", restart_delay=0.1)

    assert not supervisor.is_alive()
    started = supervisor.start()
    assert started is True
    assert supervisor.is_alive()

    metrics = supervisor.get_metrics()
    assert metrics["alive"] is True
    assert metrics["name"] == "test_proc"
    assert metrics["pid"] is not None

    supervisor.terminate_tree()
    assert not supervisor.is_alive()


def test_supervisor_terminate_tree_noop_when_none():
    """Garante que terminate_tree lida com instâncias não iniciadas (None) sem erros."""
    cmd = [sys.executable, "-c", "pass"]
    supervisor = ProcessSupervisor(command=cmd, name="none_proc")
    supervisor.terminate_tree()
    assert not supervisor.is_alive()


def test_supervisor_safe_proc_call_handles_exceptions():
    """Verifica se _safe_proc_call ignora exceções NoSuchProcess e AccessDenied."""
    mock_func = MagicMock(side_effect=psutil.NoSuchProcess(pid=9999))
    ProcessSupervisor._safe_proc_call(mock_func)
    mock_func.assert_called_once()

    mock_func_denied = MagicMock(side_effect=psutil.AccessDenied(pid=9999))
    ProcessSupervisor._safe_proc_call(mock_func_denied)
    assert mock_func_denied.call_count == 1


def test_supervisor_terminate_process_tree_with_mocks():
    """Testa a lógica interna _terminate_process_tree simulando pai e filhos psutil."""
    cmd = [sys.executable, "-c", "pass"]
    supervisor = ProcessSupervisor(command=cmd, name="mock_proc")

    mock_child = MagicMock()
    mock_parent = MagicMock()
    mock_parent.children.return_value = [mock_child]
    supervisor._psutil_proc = mock_parent

    supervisor._terminate_process_tree(timeout=0.1)

    mock_child.terminate.assert_called()
    mock_parent.terminate.assert_called()


def test_supervisor_close_popen_streams():
    """Testa o fechamento limpo de streams stdin/stdout/stderr e kill do popen."""
    cmd = [sys.executable, "-c", "pass"]
    supervisor = ProcessSupervisor(command=cmd, name="stream_proc")

    mock_popen = MagicMock()
    mock_stream = MagicMock()
    mock_stream.closed = False
    mock_popen.stdin = mock_stream
    mock_popen.stdout = mock_stream
    mock_popen.stderr = None
    mock_popen.poll.return_value = None

    supervisor._popen = mock_popen
    supervisor._close_popen_streams()

    assert mock_stream.close.call_count == 2
    mock_popen.kill.assert_called_once()


def test_supervisor_restart():
    """Verifica se a reinicialização encerra a instância antiga e inicia um novo processo."""
    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    supervisor = ProcessSupervisor(command=cmd, name="restart_proc", restart_delay=0.05)

    assert supervisor.start() is True
    old_pid = supervisor._psutil_proc.pid if supervisor._psutil_proc else None

    assert supervisor.restart(reason="teste") is True
    assert supervisor.is_alive()
    new_pid = supervisor._psutil_proc.pid if supervisor._psutil_proc else None

    assert old_pid != new_pid
    supervisor.terminate_tree()
