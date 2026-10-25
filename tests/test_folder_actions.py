"""Operações reais em arquivos temporários, com concessão e conflito de edição."""
from pathlib import Path
import pytest
from src.computer.folder_assignments import folder_grants
from src.computer.folder_actions import execute_folder_action
from src.computer.safety_gate import safety_gate


@pytest.fixture
def granted(tmp_path: Path, reset_safety_gate):
    """Autoriza somente a árvore temporária e limpa o estado mesmo se houver falha."""
    folder_grants.clear()
    safety_gate.authorize()
    grant = folder_grants.assign("a", tmp_path)
    yield grant
    folder_grants.clear()


def test_folder_isolation_and_compare_write(granted):
    """Escrita usa a versão lida; uma versão antiga não sobrescreve conteúdo novo."""
    def call(operation, **args):
        return execute_folder_action({"operation": operation, "rootId": granted.root_id, "path": "a.txt", **args}, "a")
    assert call("create", content="início")["success"]
    first = call("read")
    assert first["success"] and first["content"] == "início"
    updated = call("write", content="one", expectedVersion=first["version"])
    assert updated["success"], updated
    assert call("read")["version"] == updated["version"]
    conflict = call("write", content="two", expectedVersion=first["version"])
    assert not conflict["success"] and "FILE_CONFLICT" in conflict["error"]
    assert (granted.root / "a.txt").read_text() == "one"
    assert not execute_folder_action({"operation": "read", "rootId": granted.root_id, "path": "a.txt"}, "b")["success"]
    folder_grants.revoke("a")
    assert not call("read")["success"]


@pytest.mark.parametrize("path", ["../escape", "a.txt:stream", "NUL.txt", "trailing.", "C:\\outside", "\\outside"])
def test_paths_never_escape_or_address_special_devices(granted, path):
    """Caminhos especiais do Windows são recusados antes de criar qualquer arquivo."""
    result = execute_folder_action({"operation": "create", "path": path, "rootId": granted.root_id}, "a")
    assert not result["success"]
    assert list(granted.root.iterdir()) == []
