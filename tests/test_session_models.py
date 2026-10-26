"""Suíte de Testes para Modelos de Sessão (AgentSession).

Valida o ciclo de vida, a atribuição/liberação de abas e a serialização
dos modelos de dados das sessões de agentes IA no servidor MCP.
"""
from __future__ import annotations

import time
from src.mcp.session_models import AgentSession


def test_assign_tab_associates_tab_with_session() -> None:
    """Valida que assign_tab associa abas à sessão e lida com duplicadas de forma idempotente."""
    session = AgentSession(session_id="sess_test_101", agent_id="agent_alpha")

    # Inicialmente, a sessão não possui abas
    assert len(session.assigned_tabs) == 0
    assert not session.has_tab(1)

    # Associa a primeira aba
    session.assign_tab(1)
    assert session.has_tab(1)
    assert session.assigned_tabs == {1}

    # Associa múltiplas abas
    session.assign_tab(2)
    session.assign_tab(105)
    assert session.has_tab(2)
    assert session.has_tab(105)
    assert session.assigned_tabs == {1, 2, 105}

    # Atribuição duplicada deve manter idempotência (conjunto)
    session.assign_tab(1)
    assert len(session.assigned_tabs) == 3


def test_release_tab_and_has_tab_behaviour() -> None:
    """Valida a remoção de abas com release_tab e a checagem de exclusividade com has_tab."""
    session = AgentSession(session_id="sess_test_102")
    session.assign_tab(10)
    session.assign_tab(20)

    assert session.has_tab(10)
    assert session.has_tab(20)
    assert not session.has_tab(30)

    # Remove uma aba existente
    session.release_tab(10)
    assert not session.has_tab(10)
    assert session.has_tab(20)

    # Tenta remover aba inexistente sem levantar exceção
    session.release_tab(999)
    assert session.has_tab(20)


def test_agent_session_default_initialization_and_to_dict() -> None:
    """Valida os valores padrão na inicialização e a serialização para dicionário."""
    time_before = time.time()
    session = AgentSession(session_id="sess_test_103", agent_id="agent_beta", metadata={"role": "tester"})
    time_after = time.time()

    assert session.session_id == "sess_test_103"
    assert session.agent_id == "agent_beta"
    assert session.status == "active"
    assert time_before <= session.connected_at <= time_after
    assert session.metadata == {"role": "tester"}

    session.assign_tab(30)
    session.assign_tab(10)

    serialized = session.to_dict()
    assert serialized == {
        "sessionId": "sess_test_103",
        "agentId": "agent_beta",
        "connectedAt": session.connected_at,
        "status": "active",
        "assignedTabs": [10, 30],
        "metadata": {"role": "tester"},
    }
