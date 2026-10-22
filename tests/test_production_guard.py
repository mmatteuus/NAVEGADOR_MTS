"""Regressões unitárias do sentinela de processos de produção."""

from tests.conftest import missing_initial_pids


def test_no_initial_process_means_no_release_requirement() -> None:
    """CI sem instalação de produção não cria um falso bloqueio."""
    assert missing_initial_pids([], alive=lambda _pid: False) == []


def test_initially_alive_process_disappearing_is_detected() -> None:
    """Um PID observado vivo no início não pode desaparecer silenciosamente."""
    assert missing_initial_pids([101, 202], alive=lambda pid: pid == 101) == [202]
