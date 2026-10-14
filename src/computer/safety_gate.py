"""
Módulo de Trava de Segurança (Safety Gate) com Política Fail-Closed.

Implementa o portão de autorização obrigatório para qualquer comando do
namespace computer_*. Inicia desativado por padrão (Default-Deny) e requer
autorização explícita do usuário. Thread-safe e com histórico de auditoria.
"""

import threading
import time
from typing import Callable, List, Dict, Any, Optional

class SecurityGateError(Exception):
    """Exceção levantada quando uma ação é rejeitada por falta de autorização."""
    pass

class SafetyGate:
    """Gerenciador central de autorização para controle do sistema operacional."""

    _instance: Optional['SafetyGate'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'SafetyGate':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SafetyGate, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, '_initialized', False):
            return
        self._authorized: bool = False
        self._kill_switch_active: bool = False
        self._state_lock = threading.Lock()
        self._listeners: List[Callable[[bool, str], None]] = []
        self._audit_history: List[Dict[str, Any]] = []
        self._initialized = True

    def is_authorized(self) -> bool:
        """Retorna True se o agente possui permissão ativa para interagir no PC."""
        with self._state_lock:
            return self._authorized and not self._kill_switch_active

    def is_kill_switch_triggered(self) -> bool:
        """Informa se o interruptor de emergência (Kill-Switch) foi acionado."""
        with self._state_lock:
            return self._kill_switch_active

    def check_authorization(self, action_name: str = "Ação de automação") -> None:
        """Verifica a autorização de forma atômica; levanta exceção se desativado."""
        with self._state_lock:
            if not self._authorized or self._kill_switch_active:
                motivo = "Kill-Switch acionado" if self._kill_switch_active else "Trava desativada"
                msg = (
                    f"ERRO_SEGURANCA: Ação '{action_name}' rejeitada. "
                    f"O usuário não autorizou o controle do computador ({motivo}). "
                    "Ative o interruptor no aplicativo Desktop ou na bandeja do sistema."
                )
                self._record_audit(action_name, success=False, detail=motivo)
                raise SecurityGateError(msg)
            self._record_audit(action_name, success=True, detail="Autorizado")

    def authorize(self) -> None:
        """Concede autorização para que o agente atue no computador."""
        with self._state_lock:
            self._authorized = True
            self._kill_switch_active = False
            self._record_audit("SISTEMA", success=True, detail="Autorização concedida")
        self._notify_listeners(True, "Autorização concedida pelo usuário")

    def revoke(self, reason: str = "Ação manual do usuário") -> None:
        """Revoga imediatamente qualquer permissão de controle do computador."""
        is_kill = "KILL_SWITCH" in reason.upper()
        with self._state_lock:
            self._authorized = False
            if is_kill:
                self._kill_switch_active = True
            self._record_audit("SISTEMA", success=False, detail=f"Revogado: {reason}")
        self._notify_listeners(False, reason)

    def reset_kill_switch(self) -> None:
        """Rearma o sistema após um acionamento de Kill-Switch."""
        with self._state_lock:
            self._kill_switch_active = False
            self._record_audit("SISTEMA", success=True, detail="Kill-Switch rearmado")
        self._notify_listeners(self._authorized, "Kill-Switch rearmado")

    def add_listener(self, callback: Callable[[bool, str], None]) -> None:
        """Registra uma função de retorno para mudanças de status."""
        with self._state_lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def get_audit_history(self) -> List[Dict[str, Any]]:
        """Retorna uma cópia do registro de auditoria de segurança."""
        with self._state_lock:
            return list(self._audit_history)

    def _record_audit(self, action: str, success: bool, detail: str) -> None:
        """Registra internamente um evento de segurança."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "success": success,
            "detail": detail
        }
        self._audit_history.append(entry)
        if len(self._audit_history) > 100:
            self._audit_history.pop(0)

    def _notify_listeners(self, authorized: bool, reason: str) -> None:
        """Emite notificações para a interface e bandeja de forma segura."""
        for listener in self._listeners:
            try:
                listener(authorized, reason)
            except Exception:
                pass

# Instância padrão compartilhada do SafetyGate
safety_gate = SafetyGate()
