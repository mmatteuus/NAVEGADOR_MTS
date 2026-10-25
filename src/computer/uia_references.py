"""Referências de snapshots UIA vinculadas a controles e concessões originais."""
from __future__ import annotations

import threading
import uuid

_lock = threading.RLock()
references = {}


def clear_session_refs(session_id):
    with _lock:
        for key in [key for key in references if key[0] == session_id]:
            references.pop(key, None)


def publish(lease, controls):
    snapshot = uuid.uuid4().hex
    result = []
    pending = {}
    for index, control in enumerate(controls):
        info = control.element_info
        ref = f"uia-{snapshot}-{index}"
        pending[(lease.session_id, ref)] = {"_hwnd": lease.hwnd,
            "_generation": lease.generation, "_control": control}
        result.append({"ref": ref, "name": info.name,
                       "controlType": info.control_type, "autoId": info.automation_id})
    with _lock:
        clear_session_refs(lease.session_id)
        references.update(pending)
    return result


def resolve(session_id, ref, lease):
    with _lock:
        item = references.get((session_id, str(ref)), {})
        if item.get("_hwnd") != lease.hwnd or item.get("_generation") != lease.generation:
            raise ValueError("UIA_REF_EXPIRED: refaça a inspeção da janela atribuída")
        return item["_control"]
