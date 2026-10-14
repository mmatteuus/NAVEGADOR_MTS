"""Motor de Resiliência, Reconexão com Backoff e Gestão Segura de Sockets.

Implementa a máquina de estados de auto-cura (Self-Healing), o algoritmo de
backoff exponencial com teto rigoroso em 5 segundos e a configuração
de sockets com SO_REUSEADDR para prevenir portas presas em TIME_WAIT.
"""

from __future__ import annotations

import random
import socket
from enum import Enum
from typing import Any, Callable, List, Optional
from src.core.message_buffer import BufferedMessage, MessageBuffer


class ConnectionState(str, Enum):
    """Estados operacionais da conexão do sistema."""

    STOPPED = "STOPPED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"


class ExponentialBackoff:
    """Calcula intervalos de espera progressivos com teto de 5s e jitter."""

    def __init__(
        self,
        initial: float = 0.5,
        multiplier: float = 2.0,
        max_delay: float = 5.0,
        jitter_factor: float = 0.1,
    ) -> None:
        """Inicializa os parâmetros do algoritmo de recuo exponencial."""
        self.initial = initial
        self.multiplier = multiplier
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
        self.attempts = 0
        self._current_base = initial

    def next_delay(self) -> float:
        """Calcula o próximo intervalo (0.5s -> 1.0s -> 2.0s -> 4.0s -> teto 5.0s)."""
        if self.attempts == 0:
            base = self.initial
        else:
            base = min(self._current_base * self.multiplier, self.max_delay)

        self._current_base = base
        self.attempts += 1

        # Aplica variação aleatória de jitter para evitar tempestade de reconexão
        jitter = base * self.jitter_factor * (random.uniform(-1.0, 1.0))
        delay = max(self.initial * 0.5, min(base + jitter, self.max_delay))
        return round(delay, 3)

    def reset(self) -> None:
        """Restaura o contador de tentativas e o intervalo base inicial."""
        self.attempts = 0
        self._current_base = self.initial


def configure_socket_reuse(sock: socket.socket) -> None:
    """Configura o socket com SO_REUSEADDR para eliminar TIME_WAIT e liberar portas."""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class ResilienceManager:
    """Orquestra estados de conexão, buffer de comandos e auto-cura."""

    def __init__(
        self,
        buffer: Optional[MessageBuffer] = None,
        on_state_change: Optional[Callable[[ConnectionState, ConnectionState, str], None]] = None,
    ) -> None:
        """Inicializa o orquestrador com buffer de retenção e callbacks."""
        self.buffer = buffer or MessageBuffer()
        self.backoff = ExponentialBackoff()
        self._state = ConnectionState.STOPPED
        self._on_state_change = on_state_change

    @property
    def state(self) -> ConnectionState:
        """Retorna o estado operacional corrente."""
        return self._state

    def transition_to(self, new_state: ConnectionState, reason: str = "") -> None:
        """Efetua a transição de estado disparando notificações aos observadores."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            if self._on_state_change:
                self._on_state_change(old_state, new_state, reason)

    def handle_disconnect(self, reason: str = "") -> float:
        """Registra a desconexão, transiciona o estado e calcula o intervalo de retorno."""
        self.transition_to(ConnectionState.DEGRADED, reason)
        delay = self.backoff.next_delay()
        self.transition_to(ConnectionState.RECOVERING, f"Tentativa de auto-cura em {delay}s")
        return delay

    def handle_connected(self) -> List[BufferedMessage]:
        """Marca o retorno do sinal, zera o backoff e descarrega comandos retidos."""
        self.backoff.reset()
        self.transition_to(ConnectionState.CONNECTED, "Conexão restabelecida com sucesso")
        return self.buffer.drain()

    def should_buffer(self) -> bool:
        """Indica se novas requisições devem ser retidas no buffer circular."""
        return self._state in (ConnectionState.DEGRADED, ConnectionState.RECOVERING)

    def enqueue_command(self, payload: Any, ttl_seconds: float = 15.0) -> Optional[BufferedMessage]:
        """Enfileira um comando caso a conexão esteja instável ou degradada."""
        if self.should_buffer():
            return self.buffer.push(payload, ttl_seconds=ttl_seconds)
        return None
