"""Testes da política de recarga automática da extensão após atualização do desktop."""
from __future__ import annotations

import asyncio
import json
from src.mcp.extension_sync import ExtensionReloadPolicy
from src.mcp.ws_bridge import WebSocketBridge


def test_older_extension_requests_reload_once():
    """Extensão antiga recebe uma única ordem de recarga por versão relatada (sem loop)."""
    policy = ExtensionReloadPolicy("2.2.1")
    assert policy.should_reload({"version": "2.2.0"}) is True
    assert policy.should_reload({"version": "2.2.0"}) is False


def test_same_or_newer_extension_never_reloads():
    """Versão igual ou mais nova nunca dispara recarga."""
    policy = ExtensionReloadPolicy("2.2.1")
    assert policy.should_reload({"version": "2.2.1"}) is False
    assert policy.should_reload({"version": "2.3.0"}) is False


def test_old_extensions_have_independent_reload_budget():
    """Dois navegadores antigos recebem uma recarga independente por instância."""
    policy = ExtensionReloadPolicy("2.3.0")
    assert policy.should_reload({"version": "2.2.0", "instanceId": "chrome"}) is True
    assert policy.should_reload({"version": "2.2.0", "instanceId": "chrome"}) is False
    assert policy.should_reload({"version": "2.2.0", "instanceId": "edge"}) is True


def test_invalid_instance_id_falls_back_to_legacy_key():
    """instanceId não-string ou vazio deve usar a chave de fallback legacy."""
    policy = ExtensionReloadPolicy("2.3.0")
    # Instâncias inválidas ou vazias usam 'legacy:2.2.0'
    assert policy.should_reload({"version": "2.2.0", "instanceId": 12345}) is True
    assert policy.should_reload({"version": "2.2.0", "instanceId": ""}) is False
    assert policy.should_reload({"version": "2.2.0", "instanceId": None}) is False


def test_legacy_extension_budget_survives_reconnect():
    """Extensão antiga sem identidade não entra em laço após reconectar."""
    policy = ExtensionReloadPolicy("2.3.0")
    assert policy.should_reload({"version": "2.2.0"}) is True
    assert policy.should_reload({"version": "2.2.0"}) is False


def test_outdated_status_is_diagnostic_without_consuming_budget():
    """O diagnóstico de pasta externa não dispara nem repete a recarga."""
    policy = ExtensionReloadPolicy("2.3.0")
    payload = {"version": "2.2.0", "instanceId": "external-copy"}
    assert policy.is_outdated(payload) is True
    assert policy.should_reload(payload) is True
    assert policy.is_outdated(payload) is True


def test_non_dict_or_malformed_payload_returns_false():
    """Payloads que não são dicionários ou possuem versão malformada retornam False."""
    policy = ExtensionReloadPolicy("2.2.1")
    for payload in ("invalid", 123, True, [], None, {}, {"version": "v1.0"}, {"version": "abc"}):
        assert policy.should_reload(payload) is False
        assert policy.is_outdated(payload) is False


def test_server_hello_sets_reload_required_for_old_extension():
    """Handshake real da ponte marca reloadRequired apenas na primeira conexão antiga."""
    class FakeSocket:
        def __init__(self) -> None:
            self.sent: list[dict] = []

        async def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

    bridge = WebSocketBridge()
    hello = json.dumps({"type": "client_hello", "payload": {"version": "0.0.1"}})
    sock = FakeSocket()
    asyncio.run(bridge._process_incoming_message(hello, sock))
    asyncio.run(bridge._process_incoming_message(hello, sock))
    flags = [m["payload"]["reloadRequired"] for m in sock.sent if m["type"] == "server_hello"]
    assert flags == [True, False]
