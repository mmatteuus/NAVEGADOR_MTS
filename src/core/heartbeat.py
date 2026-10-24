"""Módulo de Heartbeat contínuo e detecção ativa de desconexões.

Implementa o protocolo de pulso (Ping/Pong) a cada 3 segundos com
timeout de 2 segundos. Detecta quedas de rede semi-abertas (Half-Open)
e aciona a rotina de auto-cura do motor de resiliência.
"""

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class HeartbeatConfig:
    """Configurações operacionais para o ciclo de batimentos cardíacos."""

    interval_seconds: float = 3.0
    timeout_seconds: float = 2.0
    max_missed_pings: int = 2


class HeartbeatManager:
    """Gerenciador do ciclo de vida de batimentos cardíacos (Heartbeat)."""

    def __init__(
        self,
        config: Optional[HeartbeatConfig] = None,
        on_failure_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Inicializa o monitor de pulso com tolerâncias e callbacks."""
        self.config = config or HeartbeatConfig()
        self._on_failure = on_failure_callback

        self._last_ping_sent: float = 0.0
        self._last_pong_received: float = 0.0
        self._waiting_pong: bool = False
        self._missed_pings: int = 0
        self._latency_ms: float = 0.0
        self._is_healthy: bool = True

    def create_ping_payload(self) -> Dict[str, Any]:
        """Gera o envelope padrão de pulso para despacho pela ponte WebSocket."""
        now = time.time()
        self._last_ping_sent = now
        self._waiting_pong = True
        return {
            "type": "ping",
            "timestamp": int(now * 1000),
        }

    def record_pong(self, pong_timestamp: Optional[float] = None) -> float:
        """Registra o recebimento do Pong, calcula a latência em ms e zera falhas."""
        now = time.time()
        self._last_pong_received = now
        self._waiting_pong = False
        self._missed_pings = 0
        self._is_healthy = True

        # Calcula a latência baseada no ping mais recente enviado
        if self._last_ping_sent > 0:
            self._latency_ms = max(0.0, (now - self._last_ping_sent) * 1000.0)
        else:
            self._latency_ms = 0.0

        return self._latency_ms

    def check_health(self, current_time: Optional[float] = None) -> bool:
        """Avalia a saúde da conexão verificando se houve estouro de timeout ou perdas."""
        now = current_time if current_time is not None else time.time()

        # Se estamos aguardando um pong e excedeu o tempo limite configurado (2s)
        if (
            self._waiting_pong
            and (now - self._last_ping_sent) > self.config.timeout_seconds
        ):
            self._missed_pings += 1
            self._waiting_pong = False  # Encerra a espera deste ciclo

        # Declara falha se o número de pings consecutivos perdidos atingir o limite (ex: 2)
        if self._missed_pings >= self.config.max_missed_pings:
            if self._is_healthy:
                self._is_healthy = False
                motivo = (
                    f"Falha de Heartbeat: {self._missed_pings} pings consecutivos "
                    f"sem resposta (timeout de {self.config.timeout_seconds}s excedido)."
                )
                if self._on_failure:
                    self._on_failure(motivo)
            return False

        return self._is_healthy

    def reset(self) -> None:
        """Reinicia todos os contadores de pulso e restaura o estado inicial."""
        self._last_ping_sent = 0.0
        self._last_pong_received = 0.0
        self._waiting_pong = False
        self._missed_pings = 0
        self._latency_ms = 0.0
        self._is_healthy = True

    @property
    def latency_ms(self) -> float:
        """Retorna a última latência calculada em milissegundos."""
        return self._latency_ms

    @property
    def missed_count(self) -> int:
        """Retorna o número de batimentos consecutivos sem resposta."""
        return self._missed_pings

    @property
    def is_healthy(self) -> bool:
        """Indica se a conexão está atualmente saudável."""
        return self._is_healthy
