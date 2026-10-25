"""Contratos da concessão humana de janelas Win32."""

import pytest
import importlib

module = importlib.import_module("src.computer.window_assignments")
from src.computer import execute_computer_action
from src.computer.safety_gate import safety_gate


def test_registry_rejects_cross_session_reuse(monkeypatch):
    registry = module.WindowAssignmentRegistry()
    monkeypatch.setattr(module.user32, "IsWindow", lambda _hwnd: 1)

    def identity(hwnd):
        value = int(hwnd.value) if hasattr(hwnd, "value") else int(hwnd)
        return (value + 1, value + 10)

    monkeypatch.setattr(module, "window_identity", identity)
    first = registry.assign("agent-a", 101)
    assert first.pid == 111
    with pytest.raises(ValueError, match="TARGET_IN_USE"):
        registry.assign("agent-b", 101)
    assert registry.resolve("agent-a") == 101
    registry.release("agent-a")
    with pytest.raises(ValueError, match="TARGET_NOT_ASSIGNED"):
        registry.resolve("agent-a", 101)


def test_registry_rejects_identity_reuse(monkeypatch):
    registry = module.WindowAssignmentRegistry()
    monkeypatch.setattr(module.user32, "IsWindow", lambda _hwnd: 1)
    identities = [(1, 2), (3, 4)]
    monkeypatch.setattr(module, "window_identity", lambda _hwnd: identities[0])
    registry.assign("agent", 42)
    identities[0] = identities[1]
    with pytest.raises(ValueError, match="TARGET_INVALID"):
        registry.resolve("agent")


def test_assignment_generation_rejects_aba(monkeypatch):
    """Revogar e reassinar o mesmo HWND invalida a concessão antiga."""
    registry = module.WindowAssignmentRegistry()
    monkeypatch.setattr(module.user32, "IsWindow", lambda _hwnd: 1)
    monkeypatch.setattr(module, "window_identity", lambda _hwnd: (1, 2))
    monkeypatch.setattr(module, "window_root", lambda hwnd: int(hwnd))
    old = registry.assign("agent", 42)
    registry.release("agent")
    registry.assign("agent", 42)
    with pytest.raises(ValueError, match="TARGET_REVOKED"):
        registry.validate(old)


def test_remote_computer_action_requires_human_assignment():
    """Sessão remota sem concessão não pode cair no cursor implícito."""
    safety_gate.authorize()
    module.window_assignments.clear()
    result = execute_computer_action("computer_mouse_move", {
        "x": 10, "y": 10, "background": True, "session_id": "unassigned"
    })
    safety_gate.revoke("fim")
    assert result["success"] is False
    assert "TARGET_NOT_ASSIGNED" in result["error"]


def test_uia_action_is_public_and_assignment_bound(monkeypatch):
    """A operação UIA passa pelo executor público e pela concessão da UI."""
    import src.computer as computer
    safety_gate.authorize()
    module.window_assignments.clear()
    monkeypatch.setattr(module.user32, "IsWindow", lambda _hwnd: 1)
    monkeypatch.setattr(module, "window_identity", lambda _hwnd: (1, 2))
    monkeypatch.setattr(module, "window_root", lambda hwnd: int(hwnd))
    module.window_assignments.assign("agent-uia", 303)
    import src.computer.uia_semantic as uia_semantic
    monkeypatch.setattr(uia_semantic, "inspect", lambda sid, hwnd: {"targetHwnd": 303, "elements": []})
    result = computer.execute_computer_action("computer_window_action", {
        "operation": "inspect", "session_id": "agent-uia"
    })
    module.window_assignments.clear()
    safety_gate.revoke("fim")
    assert result["success"] is True
    assert result["data"]["targetHwnd"] == 303
