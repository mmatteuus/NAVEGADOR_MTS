"""Suíte de Testes Multi-IA Concorrente, Limpeza de Sessões, DELETE /mcp e Multi-Túneis."""
from __future__ import annotations

import asyncio
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import patch
from aiohttp import ClientSession

from src.computer.folder_assignments import folder_grants
from src.computer.window_assignments import WindowAssignment, window_assignments
from src.core import config
from src.core.multi_tunnel_manager import MultiTunnelManager
from src.core.tunnel_config import list_tunnel_profiles, remove_tunnel_profile, save_tunnel_profile
from src.core.tunnel_service import TunnelService
from src.mcp.agent_directory import agent_directory
from src.mcp.execution_coordinator import coordinate_execution, execution_coordinator
from src.mcp.http_server import MCPHTTPServer
from src.mcp.server import MCPServer
from src.mcp.session_manager import session_manager


def test_multi_ia_parallel_tabs_and_same_tab_serialization() -> None:
    """Duas IAs em abas distintas rodam em paralelo; na mesma aba são serializadas."""
    async def scenario() -> None:
        session_manager.clear()
        execution_coordinator.clear()
        s_claude = await session_manager.get_or_create_session("stdio_12345_aa", agent_id="claude-code")
        s_gemini = await session_manager.get_or_create_session("sess_bb", agent_id="Gemini CLI")
        assert s_claude.transport == "stdio" and s_claude.pid == 12345 and s_claude.agent_family == "claude"
        assert s_gemini.transport == "http" and s_gemini.agent_family == "gemini"
        s_claude.assign_tab(10)
        s_gemini.assign_tab(20)

        async def work(sess, tid: int, delay: float) -> None:
            async with coordinate_execution(sess, "browser_click", {"tabId": tid}):
                await asyncio.sleep(delay)

        t0 = time.perf_counter()
        await asyncio.gather(work(s_claude, 10, 0.06), work(s_gemini, 20, 0.06))
        assert (time.perf_counter() - t0) < 0.11

        t1 = time.perf_counter()
        await asyncio.gather(work(s_claude, 10, 0.05), work(s_claude, 10, 0.05))
        assert (time.perf_counter() - t1) >= 0.09

        directory = {item["sessionId"]: item for item in agent_directory()}
        assert directory["stdio_12345_aa"]["agentFamily"] == "claude"
        assert directory["stdio_12345_aa"]["callCount"] == 3
        assert directory["stdio_12345_aa"]["lastCommand"] == "browser_click"
        session_manager.clear()

    asyncio.run(scenario())


def test_prune_dead_sessions_and_close_releases_grants(tmp_path: Path) -> None:
    """Sessões com PID inexistente são removidas e liberam janelas e pastas concedidas."""
    async def scenario() -> None:
        session_manager.clear()
        window_assignments.clear()
        folder_grants.clear()
        dead_sid = "stdio_99999991_dead"
        await session_manager.get_or_create_session(dead_sid, agent_id="opencode")
        window_assignments._by_session[dead_sid] = WindowAssignment(dead_sid, 1001, 1, 1, 1001)
        folder_grants.assign(dead_sid, tmp_path)

        with patch("src.mcp.session_manager.psutil.pid_exists", return_value=False):
            pruned = session_manager.prune_dead_sessions()
        assert dead_sid in pruned and session_manager.get_session(dead_sid) is None
        assert window_assignments.get(dead_sid) is None and folder_grants.get(dead_sid) is None
        session_manager.clear()

    asyncio.run(scenario())


def test_http_delete_mcp_and_gemini_origins(dynamic_port: int) -> None:
    """Valida encerramento de sessão via DELETE /mcp e suporte às origens Gemini/AI Studio."""
    async def scenario() -> None:
        session_manager.clear()
        srv = MCPHTTPServer(MCPServer(), dynamic_port)
        await srv.start()
        url = f"http://127.0.0.1:{dynamic_port}/mcp"
        try:
            async with ClientSession() as client:
                for origin in ("https://gemini.google.com", "https://aistudio.google.com"):
                    async with client.post(
                        url, headers={"Origin": origin},
                        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "Gemini"}}},
                    ) as resp:
                        assert resp.status == 200
                        sid = resp.headers["Mcp-Session-Id"]
                        assert session_manager.get_session(sid).transport == "http"
                async with client.delete(url) as r_no_hdr:
                    assert r_no_hdr.status == 400
                async with client.delete(url, headers={"Mcp-Session-Id": "inexistente"}) as r_404:
                    assert r_404.status == 404
                async with client.delete(url, headers={"Mcp-Session-Id": sid}) as r_ok:
                    assert r_ok.status == 200 and (await r_ok.json()) == {"status": "closed", "sessionId": sid}
                assert session_manager.get_session(sid) is None
        finally:
            await srv.stop()
            session_manager.clear()

    asyncio.run(scenario())


def test_multi_tunnel_profiles_and_manager(tmp_path: Path, dynamic_port: int, monkeypatch) -> None:
    """Valida persistência de múltiplos perfis e execução simultânea sem colisão de health_file."""
    fake_cfg = SimpleNamespace(app_data_dir=tmp_path, mcp_port=dynamic_port, tunnel_id="", ensure_directories=lambda: None)
    monkeypatch.setattr(config, "current_config", fake_cfg)
    p1 = save_tunnel_profile({"id": "cf_1", "name": "Cloudflare Dev", "provider": "cloudflared", "command": ["cloudflared", "tunnel"]})
    p2 = save_tunnel_profile({"id": "oa_2", "name": "OpenAI Sec", "provider": "openai", "tunnel_id": "tunnel_" + "c" * 32})
    assert len(list_tunnel_profiles()) == 2 and p1["provider"] == "cloudflared" and p2["provider"] == "openai"

    class FakeSup:
        def __init__(self, **kw): self.kw, self.alive = kw, True
        def start(self): return True
        def is_alive(self): return self.alive
        def terminate_tree(self, timeout=1.5): self.alive = False

    with patch("src.core.tunnel_service.find_tunnel_client_binary", return_value=Path("C:/Fake/tunnel-client.exe")), \
         patch("src.core.tunnel_service.get_runtime_api_key", return_value="sk-test-123"), \
         patch("src.core.tunnel_service.get_tunnel_id", return_value="tunnel_" + "a" * 32), \
         patch("src.core.tunnel_service.local_mcp_is_ready", return_value=True), \
         patch("src.core.tunnel_service.probe_tunnel_ready", return_value=True), \
         patch("src.core.tunnel_service.current_config", fake_cfg), \
         patch("src.core.tunnel_health.current_config", fake_cfg), \
         patch("src.core.tunnel_service.ProcessSupervisor", FakeSup):
        mgr = MultiTunnelManager(primary_service=TunnelService())
        assert mgr.start_tunnel("primary") and mgr.start_tunnel("cf_1") and mgr.start_tunnel("oa_2")
        st = mgr.get_status()
        assert st["tunnels"]["primary"]["healthFile"] != st["tunnels"]["oa_2"]["healthFile"]
        assert st["tunnels"]["primary"]["isActive"] and st["tunnels"]["cf_1"]["isActive"] and st["tunnels"]["oa_2"]["isActive"]
        mgr.stop_all()
        assert not mgr.get_status("primary")["isActive"]
    assert remove_tunnel_profile("cf_1") is True
