"""Módulo de Notificações Toast Nativas do Windows 11.

Responsabilidades:
- Disparo de notificações Toast usando winotify com ícones e sons do sistema.
- Prevenção contra tempestades de notificações (debouncing e controle de frequência).
- Fallback defensivo para registro em log caso o sistema de notificações falhe.
"""

import logging
import time
from typing import Dict, Optional

logger = logging.getLogger("BrowserMTS.Notifications")

# Carregamento defensivo de winotify
try:
    from winotify import Notification, audio
    _WINOTIFY_AVAILABLE = True
except ImportError:
    _WINOTIFY_AVAILABLE = False


class ToastNotifier:
    """Gerenciador central de notificações nativas do sistema operacional."""

    def __init__(self, app_id: str = "Navegador MTS - Windows 11") -> None:
        self.app_id = app_id
        self._last_sent: Dict[str, float] = {}
        self._cooldown_seconds: float = 4.0

    def _can_notify(self, key: str) -> bool:
        """Verifica se a notificação para a chave informada respeita o intervalo mínimo."""
        agora = time.time()
        ultimo = self._last_sent.get(key, 0.0)
        if agora - ultimo < self._cooldown_seconds:
            return False
        self._last_sent[key] = agora
        return True

    def notify(self, title: str, message: str, sound: str = "default") -> bool:
        """Emite uma notificação Toast nativa no Windows 11.

        Retorna True se entregue com sucesso; False caso contrário.
        """
        dedup_key = f"{title}:{message}"
        if not self._can_notify(dedup_key):
            return False

        if not _WINOTIFY_AVAILABLE:
            logger.info(f"[NOTIFICACAO] {title}: {message}")
            return False

        try:
            toast = Notification(
                app_id=self.app_id,
                title=title,
                msg=message,
                duration="short"
            )
            if sound == "alert":
                toast.set_audio(audio.Reminder, loop=False)
            elif sound == "critical":
                toast.set_audio(audio.LoopingAlarm, loop=False)
            else:
                toast.set_audio(audio.Default, loop=False)

            toast.show()
            return True
        except Exception as exc:
            logger.warning(f"Falha ao exibir notificação nativa: {exc}")
            return False

    def notify_emergency_stop(self) -> bool:
        """Notifica o acionamento emergencial do Kill-Switch (3x ESC)."""
        return self.notify(
            title="🚨 Kill-Switch de Emergência Acionado!",
            message="Controle do computador revogado e comandos cancelados imediatamente.",
            sound="critical"
        )

    def notify_service_disconnected(self, service_name: str, reason: str = "") -> bool:
        """Notifica queda ou desconexão em um serviço monitorado."""
        detalhe = f" Motivo: {reason}" if reason else ""
        return self.notify(
            title=f"⚠️ {service_name} Desconectado",
            message=f"Tentando reconexão automática em segundo plano.{detalhe}",
            sound="alert"
        )

    def notify_service_reconnected(self, service_name: str) -> bool:
        """Notifica o restabelecimento bem-sucedido de uma conexão."""
        return self.notify(
            title=f"🟢 {service_name} Reconectado",
            message="Comunicação restaurada com sucesso.",
            sound="default"
        )

    def notify_safety_gate_toggle(self, authorized: bool) -> bool:
        """Notifica a alteração na trava de autorização do Computer Use."""
        if authorized:
            return self.notify(
                title="🛡️ Computer Use Ativado",
                message="O Agente de IA agora PODE interagir com o mouse e teclado.",
                sound="default"
            )
        return self.notify(
            title="🛡️ Computer Use Bloqueado",
            message="Ações de mouse e teclado estão desautorizadas no computador.",
            sound="default"
        )


# Instância global compartilhada do notificador
notifier = ToastNotifier()
