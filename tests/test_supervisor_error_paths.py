import unittest
from unittest.mock import MagicMock, patch
import psutil
from src.core.supervisor import ProcessSupervisor

class TestProcessSupervisorErrorPaths(unittest.TestCase):
    """Testes focados em caminhos de erro e exceções do ProcessSupervisor."""

    def test_start_exceptions_line_49(self) -> None:
        """Garante que a exceção geral ao iniciar zera os atributos e retorna False."""
        sup = ProcessSupervisor(command=["dummy"])
        with patch("subprocess.Popen", side_effect=Exception("Simulated unexpected exception")):
            self.assertFalse(sup.start())
            self.assertIsNone(sup._popen)
            self.assertIsNone(sup._psutil_proc)

    def test_is_alive_exceptions(self) -> None:
        sup = ProcessSupervisor(command=["dummy"])
        self.assertFalse(sup.is_alive())
        mock_popen = MagicMock(poll=MagicMock(return_value=None))
        mock_proc = MagicMock()
        mock_proc.is_running.side_effect = psutil.NoSuchProcess(123)
        sup._popen = mock_popen
        sup._psutil_proc = mock_proc
        self.assertFalse(sup.is_alive())

    def test_safe_proc_call_exceptions(self) -> None:
        mock_func = MagicMock(side_effect=psutil.AccessDenied(123))
        ProcessSupervisor._safe_proc_call(mock_func)
        mock_func.assert_called_once()

    def test_terminate_process_tree_empty(self) -> None:
        sup = ProcessSupervisor(command=["dummy"])
        sup._terminate_process_tree(timeout=1.0)

    @patch("psutil.wait_procs")
    def test_terminate_process_tree_exceptions(self, mock_wait_procs: MagicMock) -> None:
        sup = ProcessSupervisor(command=["dummy"])
        mock_proc = MagicMock()
        mock_proc.children.return_value = []
        mock_proc.terminate.side_effect = psutil.NoSuchProcess(123)
        sup._psutil_proc = mock_proc
        mock_alive_proc = MagicMock()
        mock_alive_proc.kill.side_effect = psutil.AccessDenied(123)
        mock_wait_procs.return_value = ([], [mock_alive_proc])
        sup._terminate_process_tree(timeout=1.0)
        mock_proc.terminate.assert_called_once()
        mock_alive_proc.kill.assert_called_once()
        mock_proc.children.side_effect = psutil.AccessDenied(123)
        sup._terminate_process_tree(timeout=1.0)

    def test_close_popen_streams(self) -> None:
        sup = ProcessSupervisor(command=["dummy"])
        sup._close_popen_streams()
        mock_stream = MagicMock()
        mock_stream.closed = False
        mock_stream.close.side_effect = Exception("Erro genérico")
        mock_popen = MagicMock()
        mock_popen.stdin = mock_stream
        mock_popen.stdout = mock_stream
        mock_popen.stderr = mock_stream
        mock_popen.poll.return_value = None
        mock_popen.kill.side_effect = Exception("Erro kill")
        sup._popen = mock_popen
        sup._close_popen_streams()
        self.assertEqual(mock_stream.close.call_count, 3)
        mock_popen.kill.assert_called_once()

    def test_terminate_tree_early_return(self) -> None:
        sup = ProcessSupervisor(command=["dummy"])
        sup.terminate_tree()

    @patch("time.sleep")
    def test_restart(self, mock_sleep: MagicMock) -> None:
        sup = ProcessSupervisor(command=["dummy"], restart_delay=0.1)
        with patch.object(sup, "terminate_tree") as mock_terminate, \
             patch.object(sup, "start", return_value=True) as mock_start:
            self.assertTrue(sup.restart())
            mock_terminate.assert_called_once_with(timeout=1.5)
            mock_sleep.assert_called_once_with(0.1)
            mock_start.assert_called_once()

    def test_get_metrics(self) -> None:
        sup = ProcessSupervisor(command=["dummy"], name="teste")
        with patch.object(sup, "is_alive", return_value=False):
            metrics = sup.get_metrics()
            self.assertFalse(metrics["alive"])
        mock_proc = MagicMock(pid=123)
        mock_proc.cpu_percent.return_value = 10.5
        mock_mem = MagicMock()
        mock_mem.rss = 1048576 * 50
        mock_proc.memory_info.return_value = mock_mem
        sup._psutil_proc = mock_proc
        with patch.object(sup, "is_alive", return_value=True):
            metrics = sup.get_metrics()
            self.assertTrue(metrics["alive"])
        mock_proc.memory_info.side_effect = psutil.AccessDenied(123)
        with patch.object(sup, "is_alive", return_value=True):
            metrics = sup.get_metrics()
            self.assertFalse(metrics["alive"])

if __name__ == "__main__":
    unittest.main()
