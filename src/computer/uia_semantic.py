"""UI Automation por janela atribuída; o aplicativo pode alterar seu próprio foco."""
from __future__ import annotations

from .window_assignments import window_assignments
from .uia_tree import bounded_children
from .uia_references import clear_session_refs, publish, resolve, references as _refs
from . import uia_native


def _pattern(control, name):
    try:
        return getattr(control, name, None)
    except Exception as exc:
        if type(exc).__name__ == "NoPatternInterfaceError":
            return None
        raise


def _lease(session_id, hwnd=None):
    lease = window_assignments.get(session_id)
    if lease is None:
        raise ValueError("TARGET_NOT_ASSIGNED: atribuição humana necessária")
    window_assignments.validate(lease)
    if hwnd is not None and int(hwnd) != lease.hwnd:
        raise ValueError("TARGET_NOT_ASSIGNED: HWND não pertence à sessão")
    return lease


def _window(target):
    try:
        from pywinauto import Desktop
    except ImportError as exc:
        raise RuntimeError("UIA_UNAVAILABLE: dependência pywinauto indisponível") from exc
    return Desktop(backend="uia").window(handle=target)


def _element(session_id, hwnd, selector):
    lease = _lease(session_id, hwnd)
    if not isinstance(selector, dict):
        raise ValueError("UIA_SELECTOR_REQUIRED: seletor deve ser um objeto")
    if "ref" in selector:
        return resolve(session_id, selector["ref"], lease)
    allowed = {k: v for k, v in selector.items() if k in {"title", "auto_id", "control_type"}}
    if "name" in selector:
        allowed["title"] = selector["name"]
    if not allowed:
        raise ValueError("UIA_SELECTOR_REQUIRED: informe title, auto_id, control_type ou ref")
    return _window(lease.hwnd).child_window(**allowed).wrapper_object()


def inspect(session_id, hwnd=None):
    lease = _lease(session_id, hwnd)
    window = _window(lease.hwnd).wrapper_object()
    controls = [window, *bounded_children(window)]
    with window_assignments.effect(lease):
        refs = publish(lease, controls)
    return {"success": True, "transport": "uia", "targetHwnd": lease.hwnd, "elements": refs}


def invoke(session_id, selector, hwnd=None):
    lease = _lease(session_id, hwnd)
    control = _element(session_id, hwnd, selector)
    interface = _pattern(control, "iface_invoke")
    expand = _pattern(control, "iface_expand_collapse") if interface is None else None
    with window_assignments.effect(lease):
        if interface is not None:
            interface.Invoke()
            transport = "uia"
        elif expand is not None:
            if not lease.allow_focus:
                raise ValueError("FOCUS_REQUIRED: abrir este menu exige liberação humana do foco")
            expand.Expand()
            transport = "uia-expand"
        else:
            uia_native.invoke_button(control, lease)
            transport = "uia-bm-click"
    return {"success": True, "transport": transport, "sessionId": session_id}


def set_value(session_id, selector, value, hwnd=None):
    lease = _lease(session_id, hwnd)
    value = str(value)
    if len(value) > 1024 * 1024:
        raise ValueError("UIA_VALUE_TOO_LARGE")
    control = _element(session_id, hwnd, selector)
    interface = _pattern(control, "iface_value")
    with window_assignments.effect(lease):
        if interface is not None:
            interface.SetValue(value)
            if interface.CurrentValue != value:
                raise RuntimeError("UIA_SET_VALUE_FAILED: confirmação de texto falhou")
            transport = "uia"
        else:
            uia_native.set_text(control, lease, value)
            transport = "uia-wm-settext"
    return {"success": True, "transport": transport, "sessionId": session_id}


def read_value(session_id, selector, hwnd=None):
    lease = _lease(session_id, hwnd)
    control = _element(session_id, hwnd, selector)
    interface = _pattern(control, "iface_value")
    with window_assignments.effect(lease):
        value = interface.CurrentValue if interface is not None else control.window_text()
    return {"success": True, "transport": "uia", "value": value}
