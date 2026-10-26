"""Testes de acesso granular a janelas/pastas pelo agente do túnel e sincronização de extensão."""
from __future__ import annotations

from pathlib import Path
import pytest
from src.computer.window_assignments import window_assignments, WindowAssignment
from src.computer.folder_assignments import folder_grants
from src.computer.folder_actions import execute_folder_action
from src.core.extension_file_sync import sync_extension_files, get_source_extension_dir
from src.ui.agent_choices import choices, require_active, TUNNEL_DEFAULT_SESSION, TUNNEL_DEFAULT_LABEL


@pytest.fixture(autouse=True)
def clean_registries():
    window_assignments.clear()
    folder_grants.clear()
    yield
    window_assignments.clear()
    folder_grants.clear()


def test_agent_choices_includes_tunnel_default():
    """Valida se o túnel web está sempre listado e acessível na UI."""
    mapping = choices()
    assert TUNNEL_DEFAULT_LABEL in mapping
    assert mapping[TUNNEL_DEFAULT_LABEL] == TUNNEL_DEFAULT_SESSION
    # require_active não deve lançar erro para o túnel
    require_active(TUNNEL_DEFAULT_SESSION)


def test_tunnel_window_assignment_inherited_by_http_session():
    """Valida se uma sessão efêmera sess_... herda a janela concedida a tunnel_default."""
    # Simula concessão humana para tunnel_default
    fake_item = WindowAssignment(
        session_id=TUNNEL_DEFAULT_SESSION,
        hwnd=12345,
        thread_id=1,
        pid=1,
        root_hwnd=12345,
        allow_mouse=True,
        allow_keyboard=True,
    )
    window_assignments._by_session[TUNNEL_DEFAULT_SESSION] = fake_item

    # Sessão HTTP do túnel
    http_sid = "sess_web_chat_gpt_123"
    assert window_assignments.get(http_sid) == fake_item
    assert window_assignments.can_mouse(http_sid) is True
    assert window_assignments.can_keyboard(http_sid) is True

    # Sessão Stdio isolada que não é HTTP e não tem concessão
    stdio_sid = "agent-b"
    assert window_assignments.get(stdio_sid) is None


def test_tunnel_folder_grant_inherited_by_http_session(tmp_path: Path):
    """Valida se uma sessão efêmera sess_... consegue listar/ler a pasta concedida a tunnel_default."""
    grant = folder_grants.assign(TUNNEL_DEFAULT_SESSION, tmp_path)
    (tmp_path / "teste.txt").write_text("conteudo secreto do usuario", encoding="utf-8")

    from src.computer.safety_gate import safety_gate
    safety_gate.authorize()
    try:
        http_sid = "sess_chatgpt_actions_456"

        # 1. Agente web consulta raízes concedidas
        roots_res = execute_folder_action({"operation": "list_roots"}, http_sid)
        assert roots_res["success"] is True
        assert len(roots_res["roots"]) == 1
        root_id = roots_res["roots"][0]["rootId"]
        assert root_id == grant.root_id

        # 2. Agente web lista arquivos
        list_res = execute_folder_action({"operation": "list", "rootId": root_id}, http_sid)
        assert list_res["success"] is True
        assert any(e["name"] == "teste.txt" for e in list_res["entries"])

        # 3. Agente web lê o arquivo
        read_res = execute_folder_action({"operation": "read", "rootId": root_id, "path": "teste.txt"}, http_sid)
        assert read_res["success"] is True
        assert read_res["content"] == "conteudo secreto do usuario"

        # 4. Outro agente não autorizado continua bloqueado
        unauth_res = execute_folder_action({"operation": "read", "rootId": root_id, "path": "teste.txt"}, "agent-isolated")
        assert unauth_res["success"] is False
    finally:
        safety_gate.revoke("fim do teste")


def test_sync_extension_files_operational():
    """Valida se a rotina de auto-sincronização descobre a fonte e sincroniza diretórios."""
    src = get_source_extension_dir()
    assert src is not None
    assert (src / "manifest.json").is_file()

    synced = sync_extension_files()
    assert isinstance(synced, list)
    for p in synced:
        assert (p / "manifest.json").is_file()
