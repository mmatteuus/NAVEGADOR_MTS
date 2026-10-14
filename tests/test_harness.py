"""Módulo de Apoio e Utilitários de Teste (Test Harness).

Responsabilidades:
- Verificação de disponibilidade e liberação de portas TCP no Windows.
- Criação de subprocessos Python reais isolados para testes de supervisão.
- Cliente WebSocket simulado para testes de integração com a extensão MV3.
"""

from __future__ import annotations

import asyncio
import json
import socket
import sys
from typing import Any, Dict, Optional
import websockets
from src.core.supervisor import ProcessSupervisor


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Verifica se uma porta TCP está ocupada e aceitando conexões no host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def create_dummy_supervisor(name: str = "dummy_child") -> ProcessSupervisor:
    """Cria um ProcessSupervisor com um processo Python filho real que dorme."""
    code = "import time; time.sleep(60)"
    cmd = [sys.executable, "-c", code]
    return ProcessSupervisor(command=cmd, name=name, restart_delay=0.2)


class MockExtensionClient:
    """Simulador de cliente WebSocket representando a extensão do navegador."""

    def __init__(self, uri: str) -> None:
        self.uri = uri
        self.ws: Optional[Any] = None
        self.received_messages: list[Dict[str, Any]] = []

    async def connect(self, timeout: float = 2.0) -> None:
        """Estabelece conexão com o WebSocket Bridge do servidor MCP."""
        self.ws = await asyncio.wait_for(websockets.connect(self.uri), timeout=timeout)

    async def send_hello(self) -> None:
        """Envia a mensagem inicial de identificação da extensão (handshake)."""
        if self.ws:
            payload = {
                "type": "client_hello",
                "payload": {"version": "2.0.0", "userAgent": "Chrome/130.0"}
            }
            await self.ws.send(json.dumps(payload))

    async def receive_json(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Aguarda e decodifica a próxima mensagem JSON recebida da ponte."""
        if not self.ws:
            raise RuntimeError("Cliente mock desconectado.")
        msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
        data = json.loads(msg)
        self.received_messages.append(data)
        return data

    async def reply_to_action(self, req_id: str, result_data: Dict[str, Any]) -> None:
        """Responde a uma solicitação de ação emitida pelo servidor MCP."""
        if self.ws:
            envelope = {
                "type": "browser_response",
                "id": req_id,
                "payload": {"requestId": req_id, "result": result_data, "error": None}
            }
            await self.ws.send(json.dumps(envelope))

    async def close(self) -> None:
        """Encerra a conexão WebSocket com o servidor."""
        if self.ws:
            await self.ws.close()
            self.ws = None
