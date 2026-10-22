"""Regressões do roteamento entre múltiplas extensões conectadas."""
from src.mcp.ws_session_registry import WSSessionRegistry


class Socket:
    """Socket mínimo saudável para testar apenas seleção e identidade."""

    def __init__(self, info):
        self.info = info
        self.closed = False


def test_tab_collision_is_ambiguous_and_unique_tab_selects():
    """IDs iguais em Chrome/Edge não podem escolher pelo socket ativo."""
    reg = WSSessionRegistry()
    chrome = Socket({"instanceId": "chrome", "grantedTabIds": [7]})
    edge = Socket({"instanceId": "edge", "grantedTabIds": [7]})
    reg.register_extension(chrome, chrome.info)
    reg.register_extension(edge, edge.info)
    assert reg.select_socket("sess", 7) is None
    edge.info["grantedTabIds"] = [8]
    reg.register_extension(edge, edge.info)
    assert reg.select_socket("sess", 7) is chrome


def test_bound_session_does_not_fallback_after_disconnect():
    """Sessão vinculada permanece bloqueada até reconexão da mesma instância."""
    reg = WSSessionRegistry()
    first = Socket({"instanceId": "chrome", "grantedTabIds": [7]})
    other = Socket({"instanceId": "edge", "grantedTabIds": [7]})
    reg.register_extension(first, first.info)
    assert reg.select_socket("sess", 7) is first
    reg.register_extension(other, other.info)
    first.closed = True
    assert reg.select_socket("sess", 7) is None
    replacement = Socket(first.info)
    reg.register_extension(replacement, replacement.info)
    assert reg.select_socket("sess", 7) is replacement


def test_single_legacy_extension_remains_compatible():
    """Uma extensão sem metadados novos mantém compatibilidade histórica."""
    reg = WSSessionRegistry()
    legacy = Socket({})
    reg.register_extension(legacy, legacy.info)
    assert reg.select_socket(None, 99) is legacy
    assert reg.select_socket("sess") is legacy


def test_same_instance_overlap_recovers_after_old_socket_closes():
    """Reconexão sobreposta recupera a instância correta após o socket antigo sair."""
    reg = WSSessionRegistry()
    old = Socket({"instanceId": "chrome", "grantedTabIds": [7]})
    reg.register_extension(old, old.info)
    assert reg.select_socket("sess", 7) is old
    replacement = Socket({"instanceId": "chrome", "grantedTabIds": [7]})
    foreign = Socket({"instanceId": "edge", "grantedTabIds": [7]})
    reg.register_extension(replacement, replacement.info)
    reg.register_extension(foreign, foreign.info)
    old.closed = True
    reg.unregister(old)
    assert reg.select_socket("sess", 7) is replacement


def test_disconnected_legacy_session_does_not_switch_socket():
    """Sessão legada desconectada permanece bloqueada mesmo com outra extensão."""
    reg = WSSessionRegistry()
    old = Socket({})
    reg.register_extension(old, old.info)
    assert reg.select_socket("sess", 7) is old
    old.closed = True
    reg.unregister(old)
    other = Socket({})
    reg.register_extension(other, other.info)
    assert reg.select_socket("sess", 7) is None
