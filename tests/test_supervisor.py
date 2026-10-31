"""Suíte de Testes Unitários para o ProcessSupervisor.

Valida a inicialização de processos filhos (método start), tratamento
de exceções, flags do Windows (nt) e sustentação dos atributos de instância.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

import psutil

from src.core.supervisor import ProcessSupervisor


class TestProcessSupervisorStart(unittest.TestCase):
    """Testes focados na funcionalidade e tolerância a falhas do método start()."""

    def test_start_success_real_process(self) -> None:
        """Verifica se o start() inicia com sucesso um subprocesso válido."""
        cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
        sup = ProcessSupervisor(command=cmd, name="teste_start")
        try:
            self.assertTrue(sup.start())
            self.assertIsNotNone(sup._popen)
            self.assertIsNotNone(sup._psutil_proc)
            self.assertEqual(sup._psutil_proc.pid, sup._popen.pid)
            self.assertTrue(sup.is_alive())
        finally:
            sup.terminate_tree()

    def test_start_with_custom_cwd_and_env(self) -> None:
        """Verifica o repasse de diretório de trabalho (cwd) e variáveis de ambiente (env)."""
        mock_popen = MagicMock(pid=1234)
        mock_proc = MagicMock()
        with patch("subprocess.Popen", return_value=mock_popen) as patch_popen, \
             patch("psutil.Process", return_value=mock_proc):
            sup = ProcessSupervisor(
                command=["cmd_test"],
                name="env_cwd_test",
                cwd="/tmp",
                env={"TEST_VAR": "1"}
            )
            self.assertTrue(sup.start())
            patch_popen.assert_called_once()
            _, kwargs = patch_popen.call_args
            self.assertEqual(kwargs["cwd"], "/tmp")
            self.assertEqual(kwargs["env"], {"TEST_VAR": "1"})

    def test_start_windows_creation_flags(self) -> None:
        """Valida que no Windows (os.name == 'nt') as flags CREATE_NO_WINDOW são configuradas."""
        mock_popen = MagicMock(pid=5678)
        mock_proc = MagicMock()
        mock_startupinfo = MagicMock()
        mock_startupinfo.dwFlags = 0
        with patch("os.name", "nt"), \
             patch("subprocess.CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch("subprocess.STARTF_USESHOWWINDOW", 1, create=True), \
             patch("subprocess.STARTUPINFO", return_value=mock_startupinfo, create=True), \
             patch("subprocess.Popen", return_value=mock_popen) as patch_popen, \
             patch("psutil.Process", return_value=mock_proc):
            sup = ProcessSupervisor(command=["dummy.exe"], name="win_test")
            self.assertTrue(sup.start())
            _, kwargs = patch_popen.call_args
            self.assertEqual(kwargs["creationflags"], 0x08000000)
            self.assertIsNotNone(kwargs["startupinfo"])
            self.assertEqual(mock_startupinfo.wShowWindow, 0)

    def test_start_handles_popen_exception(self) -> None:
        """Garante que falhas no subprocess.Popen retornam False e limpam as referências."""
        with patch("subprocess.Popen", side_effect=OSError("Comando inválido")):
            sup = ProcessSupervisor(command=["invalid_command_xyz"])
            self.assertFalse(sup.start())
            self.assertIsNone(sup._popen)
            self.assertIsNone(sup._psutil_proc)

    def test_start_handles_psutil_exception(self) -> None:
        """Garante que falhas no vincular do psutil retornam False e limpam referências."""
        mock_popen = MagicMock(pid=9999)
        with patch("subprocess.Popen", return_value=mock_popen), \
             patch("psutil.Process", side_effect=psutil.NoSuchProcess(9999)):
            sup = ProcessSupervisor(command=["dummy"])
            self.assertFalse(sup.start())
            self.assertIsNone(sup._popen)
            self.assertIsNone(sup._psutil_proc)

    def test_close_popen_streams_exceptions(self) -> None:
        """Verifica se OSError e ValueError em stream.close() são suprimidos."""
        sup = ProcessSupervisor(command=["dummy"])
        mock_stream1 = MagicMock()
        mock_stream1.closed = False
        mock_stream1.close.side_effect = OSError("Erro simulado")

        mock_stream2 = MagicMock()
        mock_stream2.closed = False
        mock_stream2.close.side_effect = ValueError("Erro simulado")

        mock_popen = MagicMock()
        mock_popen.stdin = mock_stream1
        mock_popen.stdout = mock_stream2
        mock_popen.stderr = None
        # Make poll() return a code so we skip kill() in this test
        mock_popen.poll.return_value = 0
        sup._popen = mock_popen

        # Deve executar sem levantar exceção
        sup._close_popen_streams()

        mock_stream1.close.assert_called_once()
        mock_stream2.close.assert_called_once()

    def test_close_popen_streams_kill_exception(self) -> None:
        """Verifica se OSError em _popen.kill() é suprimido."""
        sup = ProcessSupervisor(command=["dummy"])
        mock_popen = MagicMock()
        mock_popen.stdin = None
        mock_popen.stdout = None
        mock_popen.stderr = None

        # Simula processo ainda vivo
        mock_popen.poll.return_value = None
        mock_popen.kill.side_effect = OSError("Erro no kill")
        sup._popen = mock_popen

        # Deve executar sem levantar exceção
        sup._close_popen_streams()

        mock_popen.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
