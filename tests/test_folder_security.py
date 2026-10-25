"""Regressões de fronteira para concessões de pastas, sem tocar dados do usuário."""
from __future__ import annotations

import os
from pathlib import Path
import pytest

from src.computer.folder_assignments import folder_grants
from src.computer.folder_actions import execute_folder_action
from src.computer.safety_gate import safety_gate
from src.mcp.router import MCPToolRouter


@pytest.fixture(autouse=True)
def clean_grants():
    folder_grants.clear(); safety_gate.authorize()
    yield
    folder_grants.clear(); safety_gate.revoke("folder test")


def _grant(path: Path, sid: str = "agent-a") -> str:
    return folder_grants.assign(sid, path).root_id


def test_root_id_is_required_and_cross_session_is_denied(tmp_path: Path):
    root_id = _grant(tmp_path)
    assert execute_folder_action({"operation": "list"}, "agent-a")["success"] is False
    assert execute_folder_action({"operation": "list", "rootId": root_id}, "agent-b")["success"] is False
    assert "FOLDER_NOT_ASSIGNED" in execute_folder_action({"operation": "list", "rootId": root_id}, "agent-b")["error"]


def test_traversal_ads_and_reserved_names_are_rejected(tmp_path: Path):
    root_id = _grant(tmp_path)
    for path in ("../outside", "nested/../../outside", "file:stream", "CON.txt"):
        result = execute_folder_action({"operation": "read", "rootId": root_id, "path": path}, "agent-a")
        assert result["success"] is False


def test_overlapping_roots_are_exclusive(tmp_path: Path):
    child = tmp_path / "child"; child.mkdir()
    _grant(tmp_path, "agent-a")
    with pytest.raises(ValueError, match="FOLDER_IN_USE"):
        folder_grants.assign("agent-b", child)


def test_revoke_invalidates_existing_root_id(tmp_path: Path):
    root_id = _grant(tmp_path)
    folder_grants.revoke("agent-a")
    result = execute_folder_action({"operation": "list", "rootId": root_id}, "agent-a")
    assert result["success"] is False and "FOLDER_NOT_ASSIGNED" in result["error"]


def test_revoke_before_write_has_no_side_effect(tmp_path: Path):
    root_id = _grant(tmp_path)
    target = tmp_path / "safe.txt"; target.write_text("before", encoding="utf-8")
    folder_grants.revoke("agent-a")
    result = execute_folder_action({"operation": "write", "rootId": root_id, "path": "safe.txt", "content": "after", "expectedVersion": "x"}, "agent-a")
    assert result["success"] is False and target.read_text(encoding="utf-8") == "before"


@pytest.mark.asyncio
async def test_router_rejects_forged_folder_session():
    class Bridge:
        is_connected = True
        async def send_action(self, *args, **kwargs):
            raise AssertionError("a sessão forjada nunca deve chegar à extensão")
    router = MCPToolRouter(ws_bridge=Bridge())
    result = await router.dispatch("computer_folder_action", {"sessionId": "agent-b", "operation": "list_roots"}, session_id="agent-a")
    assert result["isError"] is True and "forja" in result["content"][0]["text"].lower()


def test_junction_or_symlink_escape_is_denied(tmp_path: Path):
    outside = tmp_path.parent / f"mts-outside-{os.getpid()}"; outside.mkdir(exist_ok=True)
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("criação de symlink não autorizada neste runner")
    root_id = _grant(tmp_path)
    result = execute_folder_action({"operation": "list", "rootId": root_id, "path": "link"}, "agent-a")
    assert result["success"] is False
    outside.rmdir()


def test_windows_junction_escape_is_denied(tmp_path: Path):
    if os.name != "nt": pytest.skip("Windows junction test")
    import _winapi
    outside = tmp_path.parent / f"mts-junction-target-{os.getpid()}"; outside.mkdir(exist_ok=True)
    junction = tmp_path / "junction"
    try:
        _winapi.CreateJunction(str(outside), str(junction))
    except (OSError, AttributeError):
        outside.rmdir(); pytest.skip("junction indisponível neste runner")
    try:
        root_id = _grant(tmp_path)
        result = execute_folder_action({"operation": "list", "rootId": root_id, "path": "junction"}, "agent-a")
        assert result["success"] is False
    finally:
        junction.rmdir(); outside.rmdir()
