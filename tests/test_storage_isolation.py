"""Suíte de Testes de Isolamento de Armazenamento e Cookies (M-E2E).

Valida a segregação estrita de cookies, localStorage e sessões de navegação
entre múltiplos agentes de IA paralelos, prevenindo contaminação e vazamento de dados.
"""

from __future__ import annotations
import pytest
from typing import Dict, Optional


class StorageContextSandbox:
    """Modelo canônico do isolador de armazenamento e cookies por sessão de agente."""

    def __init__(self) -> None:
        self._cookies: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._local_storage: Dict[str, Dict[str, Dict[str, str]]] = {}

    def set_cookie(self, session_id: str, domain: str, name: str, value: str) -> bool:
        if not session_id or not domain or not name:
            return False
        self._cookies.setdefault(session_id, {}).setdefault(domain, {})[name] = value
        return True

    def get_cookies(self, session_id: str, domain: str) -> Dict[str, str]:
        return dict(self._cookies.get(session_id, {}).get(domain, {}))

    def set_local_storage(self, session_id: str, origin: str, key: str, val: str) -> bool:
        if not session_id or not origin or not key:
            return False
        self._local_storage.setdefault(session_id, {}).setdefault(origin, {})[key] = val
        return True

    def get_local_storage(self, session_id: str, origin: str, key: str) -> Optional[str]:
        return self._local_storage.get(session_id, {}).get(origin, {}).get(key)

    def delete_cookie(self, session_id: str, domain: str, name: str) -> bool:
        dom = self._cookies.get(session_id, {}).get(domain, {})
        if name in dom:
            del dom[name]
            return True
        return False

    def clear_session(self, session_id: str) -> None:
        self._cookies.pop(session_id, None)
        self._local_storage.pop(session_id, None)


@pytest.fixture
def storage_sandbox() -> StorageContextSandbox:
    return StorageContextSandbox()


def test_cookie_isolation_between_sessions(storage_sandbox: StorageContextSandbox) -> None:
    """Garante que cookies do Agente A não são acessíveis nem vazados para o Agente B."""
    domain = "https://app.corp.test"

    storage_sandbox.set_cookie("agent_alpha", domain, "auth_token", "jwt_alpha_secret_xyz")
    storage_sandbox.set_cookie("agent_alpha", domain, "user_id", "usr_9981")

    cookies_b = storage_sandbox.get_cookies("agent_beta", domain)
    assert "auth_token" not in cookies_b, "Vazamento crítico: Agente B acessou cookie do Agente A!"
    assert cookies_b == {}, "Agente B deveria ver armazenamento de cookies vazio para este domínio"

    storage_sandbox.set_cookie("agent_beta", domain, "auth_token", "jwt_beta_different_key")
    assert storage_sandbox.get_cookies("agent_alpha", domain)["auth_token"] == "jwt_alpha_secret_xyz"
    assert storage_sandbox.get_cookies("agent_beta", domain)["auth_token"] == "jwt_beta_different_key"


def test_local_storage_partitioning(storage_sandbox: StorageContextSandbox) -> None:
    """Valida o particionamento de localStorage entre múltiplos agentes."""
    origin = "https://painel.financas.test"

    storage_sandbox.set_local_storage("agent_alpha", origin, "api_key", "sec_live_1234")
    storage_sandbox.set_local_storage("agent_beta", origin, "api_key", "sec_dev_5678")

    assert storage_sandbox.get_local_storage("agent_alpha", origin, "api_key") == "sec_live_1234"
    assert storage_sandbox.get_local_storage("agent_beta", origin, "api_key") == "sec_dev_5678"
    assert storage_sandbox.get_local_storage("agent_gamma", origin, "api_key") is None


def test_cookie_mutation_protection(storage_sandbox: StorageContextSandbox) -> None:
    """Garante que remoção de cookie pelo Agente B não remove nem corrompe cookie do Agente A."""
    domain = "https://ecommerce.test"
    storage_sandbox.set_cookie("agent_alpha", domain, "session_id", "alpha_sess_val")

    deleted = storage_sandbox.delete_cookie("agent_beta", domain, "session_id")
    assert deleted is False, "Agente B não deve conseguir deletar chave que não existe em sua partição"

    alpha_cookies = storage_sandbox.get_cookies("agent_alpha", domain)
    assert alpha_cookies.get("session_id") == "alpha_sess_val"


def test_session_cleanup_preserves_sibling_storage(storage_sandbox: StorageContextSandbox) -> None:
    """Valida que expurgo de sessão do Agente A não remove os dados do Agente B."""
    domain, origin = "https://banco.test", "https://banco.test"

    storage_sandbox.set_cookie("agent_alpha", domain, "token", "tok_a")
    storage_sandbox.set_local_storage("agent_alpha", origin, "cache", "data_a")
    storage_sandbox.set_cookie("agent_beta", domain, "token", "tok_b")
    storage_sandbox.set_local_storage("agent_beta", origin, "cache", "data_b")

    storage_sandbox.clear_session("agent_alpha")

    assert storage_sandbox.get_cookies("agent_alpha", domain) == {}
    assert storage_sandbox.get_local_storage("agent_alpha", origin, "cache") is None
    assert storage_sandbox.get_cookies("agent_beta", domain) == {"token": "tok_b"}
    assert storage_sandbox.get_local_storage("agent_beta", origin, "cache") == "data_b"
