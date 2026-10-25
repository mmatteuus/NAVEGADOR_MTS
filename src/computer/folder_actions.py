"""Arquivos por concessão humana; comparação e escrita sob handle exclusivo."""
from __future__ import annotations

import os
from .folder_assignments import folder_grants
from .folder_handles import LockedHandle, MAX_FILE_BYTES
from .folder_paths import pinned_directories
from .safety_gate import safety_gate


def _execute(params, session_id):
    op = params.get("operation", "list_roots")
    if op == "list_roots":
        grant = folder_grants.get(session_id)
        roots = [{"rootId": grant.root_id, "path": str(grant.root)}] if grant else []
        return {"success": True, "roots": roots}
    if op not in {"list", "read", "create", "mkdir", "write"}:
        raise ValueError("FOLDER_OPERATION_UNSUPPORTED")
    grant, target = folder_grants.resolve(session_id, params.get("path", ""), params.get("rootId"))
    if op != "list" and target == grant.root:
        raise ValueError("FOLDER_PATH_REQUIRED")
    data = params.get("content", "")
    if not isinstance(data, str):
        raise ValueError("FILE_CONTENT_INVALID")
    data = data.encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("FILE_TOO_LARGE: limite de 1 MiB")
    with pinned_directories(target if op == "list" else target.parent) as handles:
        if handles[grant.root].identity() != grant.identity:
            raise ValueError("FOLDER_REPLACED: a raiz escolhida foi substituída")
        with folder_grants.commit(grant):
            safety_gate.check_authorization("computer_folder_action")
            if op == "list":
                entries = []
                with os.scandir(target) as listing:
                    for item in listing:
                        if len(entries) == 200:
                            return {"success": True, "entries": entries, "truncated": True}
                        entries.append({"name": item.name, "directory": item.is_dir(follow_symlinks=False)})
                return {"success": True, "entries": entries, "truncated": False}
            if op == "mkdir":
                os.mkdir(target)
                return {"success": True, "path": params["path"]}
            if op == "write" and not isinstance(params.get("expectedVersion"), str):
                raise ValueError("FILE_VERSION_REQUIRED")
            with LockedHandle(target, write=op != "read", create=op == "create") as file:
                before = file.read()
                version = file.version(before)
                if op == "read":
                    return {"success": True, "content": before.decode("utf-8"), "version": version}
                if op == "write" and version != params["expectedVersion"]:
                    raise ValueError("FILE_CONFLICT: arquivo mudou desde a leitura")
                try:
                    file.write(data)
                except OSError:
                    # Recuperação de erro de I/O; não se promete atomicidade contra queda de energia.
                    file.write(before)
                    raise
                return {"success": True, "version": file.version(data)}


def execute_folder_action(params: dict, session_id: str) -> dict:
    """Nunca concede diretórios; o agente usa somente um rootId já autorizado."""
    try:
        safety_gate.check_authorization("computer_folder_action")
        if not session_id:
            raise ValueError("FOLDER_SESSION_REQUIRED")
        return _execute(params, session_id)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
