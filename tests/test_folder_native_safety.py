"""Barreiras reais Win32 contra escritores, troca de diretório e hardlinks."""
from __future__ import annotations

import os
import pytest
from src.computer.folder_actions import execute_folder_action
from src.computer.folder_assignments import folder_grants
from src.computer.folder_handles import LockedHandle
from src.computer.folder_paths import pinned_directories
from src.computer.safety_gate import safety_gate


@pytest.fixture(autouse=True)
def cleanup(reset_safety_gate):
    """Nenhuma concessão de um teste é reaproveitada pelo próximo."""
    folder_grants.clear()
    safety_gate.authorize()
    yield
    folder_grants.clear()


def test_windows_handle_excludes_external_writer(tmp_path):
    """O próprio kernel impede um escritor entre comparação e gravação."""
    target = tmp_path / "locked.txt"
    target.write_text("preservar")
    with LockedHandle(target, write=True) as locked:
        with pytest.raises(PermissionError):
            target.write_text("intruso")
        assert locked.read() == b"preservar"
    assert target.read_text() == "preservar"


def test_pinned_parent_cannot_be_renamed(tmp_path):
    """Reter o ancestral impede troca de caminho enquanto a operação está aberta."""
    root = tmp_path / "root"
    root.mkdir()
    with pinned_directories(root):
        with pytest.raises(PermissionError):
            root.rename(tmp_path / "moved")
    assert root.is_dir()


def test_hardlink_cannot_modify_file_outside_grant(tmp_path):
    """Um segundo nome interno não autoriza alterar o mesmo arquivo externo."""
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("intocado")
    os.link(outside, root / "link.txt")
    grant = folder_grants.assign("a", root)
    result = execute_folder_action({"operation": "read", "rootId": grant.root_id, "path": "link.txt"}, "a")
    assert not result["success"] and "HARDLINK_DENIED" in result["error"]
    assert outside.read_text() == "intocado"


def test_root_replacement_requires_new_human_grant(tmp_path):
    """Recriar o mesmo caminho não reaproveita a identidade da raiz removida."""
    root = tmp_path / "root"
    root.mkdir()
    grant = folder_grants.assign("a", root)
    root.rename(tmp_path / "old")
    root.mkdir()
    result = execute_folder_action({"operation": "create", "rootId": grant.root_id, "path": "new.txt"}, "a")
    assert not result["success"] and "FOLDER_REPLACED" in result["error"]
    assert list(root.iterdir()) == []


def test_ancestor_roots_are_exclusive_and_old_grants_expire(tmp_path):
    """Um agente não assume subpasta do outro nem reutiliza concessão revogada."""
    child = tmp_path / "child"
    child.mkdir()
    old = folder_grants.assign("a", tmp_path)
    with pytest.raises(ValueError, match="FOLDER_IN_USE"):
        folder_grants.assign("b", child)
    folder_grants.revoke("a")
    new = folder_grants.assign("a", tmp_path)
    assert old.root_id != new.root_id
    result = execute_folder_action({"operation": "list", "rootId": old.root_id}, "a")
    assert not result["success"]
