"""Supervisor de processos filhos com encerramento limpo em árvore via psutil.

Gerencia o ciclo de vida de binários dependentes (ex: tunnel-client.exe e runners),
garantindo auto-recuperação em <= 500ms caso o processo morra e evitando
o acúmulo de processos órfãos através de encerramento em cascata.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, List, Optional
import psutil


class ProcessSupervisor:
    """Supervisiona a execução, saúde e reinicialização de um processo filho."""

    def __init__(
        self,
        command: List[str],
        name: str = "processo_supervisionado",
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        restart_delay: float = 0.5,
    ) -> None:
        """Configura o comando, nome de identificação e tempo de auto-cura."""
        self.command = command
        self.name = name
        self.cwd = cwd
        self.env = env
        self.restart_delay = restart_delay  # Reinício rápido em <= 500ms
        self._popen: Optional[subprocess.Popen[Any]] = None
        self._psutil_proc: Optional[psutil.Process] = None

    def start(self) -> bool:
        """Inicia o processo filho e vincula o monitoramento do psutil."""
        try:
            creationflags = 0
            startupinfo = None
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            self._popen = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            self._psutil_proc = psutil.Process(self._popen.pid)
            return True
        except Exception:
            self._popen = None
            self._psutil_proc = None
            return False

    def is_alive(self) -> bool:
        """Verifica se o processo continua ativo no sistema operacional."""
        if self._popen is None or self._popen.poll() is not None:
            return False
        if self._psutil_proc is None:
            return False
        try:
            return self._psutil_proc.is_running() and self._psutil_proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def terminate_tree(self, timeout: float = 2.0) -> None:
        """Encerra graciosamente toda a árvore de processos (pai e filhos)."""
        if self._popen is None or self._psutil_proc is None:
            return

        try:
            parent = self._psutil_proc
            children = parent.children(recursive=True)
            all_procs = children + [parent]

            # 1. Envia sinal de término gracioso para todos os processos
            for proc in all_procs:
                try: proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied): pass

            # 2. Aguarda a liberação dos processos pelo kernel do Windows
            _, alive = psutil.wait_procs(all_procs, timeout=timeout)

            # 3. Se algum processo filho resistir, força a finalização imediata
            for proc in alive:
                try: proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied): pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        finally:
            if self._popen is not None:
                for stream in (self._popen.stdin, self._popen.stdout, self._popen.stderr):
                    if stream is not None and not stream.closed:
                        try: stream.close()
                        except Exception: pass
                if self._popen.poll() is None:
                    self._popen.kill()
            self._popen = None
            self._psutil_proc = None

    def restart(self, reason: str = "") -> bool:
        """Mata a árvore anterior, aguarda o intervalo de liberação e reinicia."""
        self.terminate_tree(timeout=1.5)
        if self.restart_delay > 0:
            time.sleep(self.restart_delay)
        return self.start()

    def get_metrics(self) -> Dict[str, Any]:
        """Coleta métricas de consumo de memória, uso de CPU e integridade."""
        empty_res = {"name": self.name, "alive": False, "pid": None, "cpu_percent": 0.0, "memory_mb": 0.0}
        if not self.is_alive() or self._psutil_proc is None:
            return empty_res

        try:
            mem_info = self._psutil_proc.memory_info()
            return {
                "name": self.name,
                "alive": True,
                "pid": self._psutil_proc.pid,
                "cpu_percent": self._psutil_proc.cpu_percent(interval=0.0),
                "memory_mb": round(mem_info.rss / (1024 * 1024), 2),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return empty_res
