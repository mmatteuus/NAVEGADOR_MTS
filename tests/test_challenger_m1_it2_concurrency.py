"""Suíte de Desafio Concorrente — Marco 1 Iteração 2 (Challenger 1).

Testa empiricamente estresse extremo de concorrência multissessão:
1. Rajada massiva simultânea de criação de abas por múltiplos agentes.
2. Fechamento concorrente de abas e limpeza do mapa de posse.
3. Tentativas simultâneas de invasão/fechamento indevido durante rajadas.
"""
from __future__ import annotations
import asyncio
import random
import pytest
from src.mcp import MCPToolRouter, WebSocketBridge
from src.mcp.session_manager import session_manager


class MockConcurrentWSBridge:
    """Simula bridge WebSocket de alta concorrência com latência realista."""
    def __init__(self) -> None:
        self.is_connected = True
        self.tab_counter = 1000
        self._lock = asyncio.Lock()

    async def send_action(self, action: str, params: dict, **kwargs) -> dict:
        await asyncio.sleep(random.uniform(0.001, 0.015))
        if action in ("browser_manage_tabs", "browser_new_tab"):
            sub_act = params.get("action")
            if sub_act == "new" or action == "browser_new_tab":
                async with self._lock:
                    self.tab_counter += 1
                    assigned_id = self.tab_counter
                return {"success": True, "data": {"tabId": assigned_id, "url": params.get("url", "about:blank")}}
            elif sub_act == "close":
                return {"success": True, "data": {"closed": True, "tabId": params.get("tabId")}}
        return {"success": True, "data": {"action": action, "ok": True}}


def test_concurrent_burst_tab_creation_multi_session() -> None:
    """Desafio: 10 agentes criam simultaneamente 5 abas cada (50 abas)."""
    async def _run():
        session_manager.clear()
        try:
            bridge = MockConcurrentWSBridge()
            router = MCPToolRouter(ws_bridge=bridge)
            num_agents = 10
            tabs_per_agent = 5
            created_tabs = {}

            async def agent_create_tab(agent_idx: int, tab_idx: int):
                sid = f"agent_sess_{agent_idx}"
                res = await router.dispatch(
                    "browser_manage_tabs",
                    {"action": "new", "url": f"https://agent{agent_idx}.org/page{tab_idx}", "sessionId": sid},
                    session_id=sid
                )
                assert res["isError"] is False
                assert len(res["content"]) > 0

            tasks = [agent_create_tab(a, t) for a in range(num_agents) for t in range(tabs_per_agent)]
            random.shuffle(tasks)
            await asyncio.gather(*tasks)

            total_registered = 0
            all_tabs = set()
            for a in range(num_agents):
                sid = f"agent_sess_{a}"
                sess = session_manager.get_session(sid)
                assert sess is not None, f"Sessão {sid} deve existir"
                assert len(sess.assigned_tabs) == tabs_per_agent, f"{sid} deve ter {tabs_per_agent} abas"
                total_registered += len(sess.assigned_tabs)
                for tid in sess.assigned_tabs:
                    assert tid not in all_tabs, f"Aba {tid} foi duplicada entre sessões!"
                    all_tabs.add(tid)
                    # Não pode ser acessada por anônimo nem por outro agente
                    assert session_manager.validate_tab_access(sid, tid) is True
                    assert session_manager.validate_tab_access(None, tid) is False
                    other_sid = f"agent_sess_{(a + 1) % num_agents}"
                    assert session_manager.validate_tab_access(other_sid, tid) is False

            assert total_registered == num_agents * tabs_per_agent == 50
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_concurrent_tab_close_and_cross_session_attack() -> None:
    """Desafio: Fechamento concorrente de abas e bloqueio de tentativas de fechamento hostil."""
    async def _run():
        session_manager.clear()
        try:
            bridge = MockConcurrentWSBridge()
            router = MCPToolRouter(ws_bridge=bridge)
            # Prepara 2 sessões legítimas com 10 abas cada
            for tid in range(101, 111):
                session_manager.assign_tab_to_session("legit_A", tid)
            for tid in range(201, 211):
                session_manager.assign_tab_to_session("legit_B", tid)

            attacker_sid = "evil_agent"
            # Atacante tenta fechar todas as abas da sessão A simultaneamente
            async def attack_close(tid: int):
                res = await router.dispatch(
                    "browser_manage_tabs",
                    {"action": "close", "tabId": tid, "sessionId": attacker_sid},
                    session_id=attacker_sid
                )
                assert res["isError"] is True
                assert "Acesso recusado" in res["content"][0]["text"]

            # Dono legítimo fecha suas próprias abas simultaneamente
            async def legit_close(sid: str, tid: int):
                res = await router.dispatch(
                    "browser_manage_tabs",
                    {"action": "close", "tabId": tid, "sessionId": sid},
                    session_id=sid
                )
                assert res["isError"] is False

            tasks = []
            for tid in range(101, 111):
                tasks.append(attack_close(tid))
                tasks.append(legit_close("legit_A", tid))
            for tid in range(201, 211):
                tasks.append(attack_close(tid))
                tasks.append(legit_close("legit_B", tid))

            random.shuffle(tasks)
            await asyncio.gather(*tasks)

            # Todas as abas legítimas devem ter sido liberadas após o fechamento
            sess_a = session_manager.get_session("legit_A")
            sess_b = session_manager.get_session("legit_B")
            assert len(sess_a.assigned_tabs) == 0, "Todas as abas de legit_A devem ter sido liberadas"
            assert len(sess_b.assigned_tabs) == 0, "Todas as abas de legit_B devem ter sido liberadas"
        finally:
            session_manager.clear()

    asyncio.run(_run())
