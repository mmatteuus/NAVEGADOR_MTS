"""Limites independentes de UIA, referências e captura por concessão."""
from __future__ import annotations
from contextlib import nullcontext
from types import SimpleNamespace
import pytest
from src.computer import uia_semantic as uia
from src.computer.uia_tree import bounded_children
from src.computer import window_capture


def test_bounded_children_never_yields_beyond_limit():
    class Node:
        def __init__(self, depth=0): self.depth = depth
        def children(self): return [Node(self.depth + 1) for _ in range(20)] if self.depth < 4 else []
    assert len(list(bounded_children(Node(), limit=7, max_depth=2))) == 7


def test_uia_reference_generation_is_rejected(monkeypatch):
    lease = SimpleNamespace(session_id="agent", hwnd=77, generation=2)
    monkeypatch.setattr(uia, "_lease", lambda *_args: lease)
    uia._refs[("agent", "old")] = {"_hwnd": 77, "_generation": 1}
    with pytest.raises(ValueError, match="UIA_REF_EXPIRED"):
        uia._element("agent", None, {"ref": "old"})


def test_invoke_does_not_fallback_after_invoke_failure(monkeypatch):
    lease = SimpleNamespace(session_id="agent", hwnd=77, generation=1)
    called = []
    control = SimpleNamespace(iface_invoke=SimpleNamespace(Invoke=lambda: (_ for _ in ()).throw(RuntimeError("boom"))))
    monkeypatch.setattr(uia, "_lease", lambda *_args: lease)
    monkeypatch.setattr(uia, "_element", lambda *_args: control)
    monkeypatch.setattr(uia.window_assignments, "effect", lambda _: nullcontext())
    monkeypatch.setattr(uia.uia_native, "invoke_button", lambda *_args: called.append(True))
    with pytest.raises(RuntimeError, match="boom"):
        uia.invoke("agent", {"title": "x"})
    assert called == []


def test_value_pattern_requires_readback_match(monkeypatch):
    lease = SimpleNamespace(session_id="agent", hwnd=77, generation=1)
    class Value:
        CurrentValue = "old"
        def SetValue(self, _value): pass
    monkeypatch.setattr(uia, "_lease", lambda *_args: lease)
    monkeypatch.setattr(uia, "_element", lambda *_args: SimpleNamespace(iface_value=Value()))
    monkeypatch.setattr(uia.window_assignments, "effect", lambda _: nullcontext())
    with pytest.raises(RuntimeError, match="confirmação"):
        uia.set_value("agent", {"title": "x"}, "new")


def test_revoked_effect_blocks_invoke(monkeypatch):
    lease = SimpleNamespace(session_id="agent", hwnd=77, generation=1)
    invoked = []
    control = SimpleNamespace(iface_invoke=SimpleNamespace(Invoke=lambda: invoked.append(True)))
    monkeypatch.setattr(uia, "_lease", lambda *_args: lease)
    monkeypatch.setattr(uia, "_element", lambda *_args: control)
    def revoked(_lease):
        raise ValueError("TARGET_REVOKED: atribuição foi revogada")
    monkeypatch.setattr(uia.window_assignments, "effect", revoked)
    with pytest.raises(ValueError, match="TARGET_REVOKED"):
        uia.invoke("agent", {"title": "x"})
    assert invoked == []


def test_capture_rejects_foreign_hwnd_before_grab(monkeypatch):
    lease = SimpleNamespace(hwnd=77)
    monkeypatch.setattr(window_capture.window_assignments, "get", lambda _: lease)
    monkeypatch.setattr(window_capture.window_assignments, "validate", lambda _: 77)
    monkeypatch.setattr(window_capture.ImageGrab, "grab", lambda **_: (_ for _ in ()).throw(AssertionError("captured")))
    with pytest.raises(ValueError, match="não pertence"):
        window_capture.capture("agent", hwnd=88)


def test_menu_expansion_requires_human_focus_grant(monkeypatch):
    """Menu que abre popup não recebe permissão de foco da chamada do agente."""
    lease = SimpleNamespace(allow_focus=False)
    expanded = []
    control = SimpleNamespace(iface_expand_collapse=SimpleNamespace(Expand=lambda: expanded.append(True)))
    monkeypatch.setattr(uia, "_lease", lambda *_args: lease)
    monkeypatch.setattr(uia, "_element", lambda *_args: control)
    monkeypatch.setattr(uia.window_assignments, "effect", lambda _: nullcontext())
    with pytest.raises(ValueError, match="FOCUS_REQUIRED"):
        uia.invoke("agent", {"title": "Help", "allow_focus": True})
    assert expanded == []
