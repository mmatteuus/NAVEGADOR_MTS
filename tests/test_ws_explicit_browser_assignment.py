"""Atribuição humana escolhe o perfil correto mesmo com IDs de guia iguais."""
from src.mcp.ws_session_registry import WSSessionRegistry


class Socket:
    closed = False


def test_two_profiles_with_equal_tab_id_route_by_explicit_owner():
    """Agentes distintos chegam somente ao navegador que recebeu a concessão."""
    registry = WSSessionRegistry()
    first, second = Socket(), Socket()
    registry.register_extension(first, {"instanceId": "profile-a", "grantedTabIds": [42],
        "tabAssignments": {"42": "chat-a"}})
    registry.register_extension(second, {"instanceId": "profile-b", "grantedTabIds": [42],
        "tabAssignments": {"42": "chat-b"}})
    assert registry.select_socket("chat-a", 42) is first
    assert registry.select_socket("chat-b", 42) is second
    assert registry.select_socket("unknown", 42) is None


def test_assignment_without_current_grant_is_ignored():
    """Metadado de dono antigo não restaura uma guia cuja concessão foi removida."""
    registry = WSSessionRegistry()
    first = Socket()
    registry.register_extension(first, {"instanceId": "a", "grantedTabIds": [],
        "tabAssignments": {"42": "chat-a"}})
    assert registry.select_socket("chat-a", 42) is None
