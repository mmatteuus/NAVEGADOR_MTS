"""Testes adversariais de violação de posse de abas e spoofing de sessão no router.

Valida que requisições concorrentes de agentes rivais não conseguem acessar
    abas alheias e que a criação não concede posse implicitamente.
"""
from __future__ import annotations
import asyncio
from src.mcp import MCPToolRouter, WebSocketBridge
from src.mcp.session_manager import session_manager


def test_adversarial_cross_session_tab_spoofing() -> None:
    """Verifica que 20 agentes concorrentes não conseguem operar aba de outra sessão."""
    async def _run():
        session_manager.clear()
        target_sid = "sess_legitima"
        target_tab = 777
        session_manager.assign_tab_to_session(target_sid, target_tab)

        bridge = WebSocketBridge(port=9300)
        bridge._active_socket = object()
        bridge.send_action = lambda a, p, **kw: asyncio.sleep(0.001, result={"success": True, "data": {"ok": 1}})
        router = MCPToolRouter(ws_bridge=bridge)

        async def attempt_access(sid: str, expected_success: bool):
            res = await router.dispatch("browser_click", {"tabId": target_tab, "selector": "#b"}, session_id=sid)
            if expected_success:
                assert res.get("isError") is not True
            else:
                assert res.get("isError") is True
                assert "Acesso recusado" in res["content"][0]["text"]

        # 1 agente legítimo + 19 agentes invasores disparando simultaneamente
        tasks = [attempt_access(target_sid, True)]
        for i in range(19):
            tasks.append(attempt_access(f"sess_invasora_{i}", False))

        await asyncio.gather(*tasks)

    asyncio.run(_run())


def test_adversarial_concurrent_tab_creation_ownership() -> None:
    """Verifica que criação concorrente de abas por 25 sessões mantém isolamento estrito."""
    async def _run():
        session_manager.clear()
        bridge = WebSocketBridge(port=9301)
        bridge._active_socket = object()

        # Simula resposta do browser_manage_tabs criando abas com IDs únicos
        async def mock_new_tab(act: str, params: dict, session_id: str = None):
            tab_id = int(params["url"].split("/")[-1])
            return {"success": True, "data": {"tabId": tab_id, "url": params["url"]}}

        bridge.send_action = mock_new_tab
        router = MCPToolRouter(ws_bridge=bridge)

        async def create_and_verify(idx: int):
            sid = f"sess_agent_{idx}"
            tab_id = 2000 + idx
            res = await router.dispatch("browser_manage_tabs", {"action": "new", "url": f"https://site.com/{tab_id}"}, session_id=sid)
            assert res.get("isError") is not True
            # A posse exige atribuição humana explícita no popup.
            sess = session_manager.get_session(sid)
            assert sess is None or not sess.has_tab(tab_id)
            session_manager.assign_tab_to_session(sid, tab_id)
            assert session_manager.validate_tab_access(sid, tab_id) is True
            assert session_manager.validate_tab_access(f"other_{sid}", tab_id) is False

        await asyncio.gather(*(create_and_verify(i) for i in range(25)))

    asyncio.run(_run())
