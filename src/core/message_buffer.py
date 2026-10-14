"""Buffer Circular de Mensagens com retenção temporária (TTL).

Este módulo implementa uma fila circular thread-safe projetada para
reter requisições do MCP durante oscilações momentâneas de rede ou
reconexão do WebSocket, evitando que comandos sejam perdidos.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, List, Optional


@dataclass
class BufferedMessage:
    """Representa uma mensagem armazenada temporariamente no buffer."""

    payload: Any
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 15.0

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Verifica se a mensagem ultrapassou seu tempo limite de retenção (TTL)."""
        now = current_time if current_time is not None else time.time()
        return (now - self.created_at) > self.ttl_seconds


class MessageBuffer:
    """Fila circular com controle de TTL e descarte automático de expirados."""

    def __init__(self, max_capacity: int = 100, default_ttl: float = 15.0) -> None:
        """Inicializa o buffer circular com capacidade e TTL padrão de 15 segundos."""
        self._max_capacity = max_capacity
        self._default_ttl = default_ttl
        self._queue: deque[BufferedMessage] = deque(maxlen=max_capacity)
        self._lock = Lock()

    def push(
        self,
        payload: Any,
        ttl_seconds: Optional[float] = None,
        msg_id: Optional[str] = None,
    ) -> BufferedMessage:
        """Adiciona uma nova mensagem à fila circular com segurança de thread."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        msg = (
            BufferedMessage(payload=payload, ttl_seconds=ttl)
            if msg_id is None
            else BufferedMessage(payload=payload, id=msg_id, ttl_seconds=ttl)
        )

        with self._lock:
            # O deque com maxlen descarta automaticamente o item mais antigo se atingir o teto
            self._queue.append(msg)
        return msg

    def pop(self) -> Optional[BufferedMessage]:
        """Remove e retorna a mensagem mais antiga ainda válida, expurgando as expiradas."""
        with self._lock:
            now = time.time()
            while self._queue:
                candidate = self._queue.popleft()
                if not candidate.is_expired(now):
                    return candidate
            return None

    def drain(self) -> List[BufferedMessage]:
        """Esvazia o buffer e retorna todas as mensagens válidas em ordem FIFO."""
        with self._lock:
            now = time.time()
            valid_messages: List[BufferedMessage] = []
            while self._queue:
                candidate = self._queue.popleft()
                if not candidate.is_expired(now):
                    valid_messages.append(candidate)
            return valid_messages

    def cleanup_expired(self) -> int:
        """Remove mensagens cujo TTL já expirou, retornando a quantidade descartada."""
        with self._lock:
            now = time.time()
            initial_count = len(self._queue)
            surviving = deque(
                (msg for msg in self._queue if not msg.is_expired(now)),
                maxlen=self._max_capacity,
            )
            self._queue = surviving
            return initial_count - len(self._queue)

    def is_empty(self) -> bool:
        """Informa se o buffer está vazio."""
        with self._lock:
            return len(self._queue) == 0

    def clear(self) -> None:
        """Limpa completamente todas as mensagens do buffer."""
        with self._lock:
            self._queue.clear()

    def __len__(self) -> int:
        """Retorna o número de mensagens presentes no buffer."""
        with self._lock:
            return len(self._queue)
