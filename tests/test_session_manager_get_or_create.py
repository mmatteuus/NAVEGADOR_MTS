"""Testes unitários dedicados para o método get_or_create_session do SessionManager."""
from __future__ import annotations

import asyncio
import pytest
from src.mcp.session_manager import SessionManager


@pytest.mark.asyncio
async def test_get_or_create_session_explicit_id_and_agent() -> None:
    """Valida a criação de sessão com session_id e agent_id informados explicitamente."""
    sm = SessionManager()
    session = await sm.get_or_create_session(session_id="sess_custom_101", agent_id="agent_alpha")

    assert session is not None
    assert session.session_id == "sess_custom_101"
    assert session.agent_id == "agent_alpha"
    assert session.status == "active"
    assert sm.get_session("sess_custom_101") is session


@pytest.mark.asyncio
async def test_get_or_create_session_auto_generated_id() -> None:
    """Valida a geração automática de ID único quando session_id é None, vazio ou espaços."""
    sm = SessionManager()

    # Teste com None
    sess_none = await sm.get_or_create_session(session_id=None, agent_id="agent_auto")
    assert sess_none.session_id.startswith("sess_")
    assert len(sess_none.session_id) == 17  # 'sess_' + 12 hex

    # Teste com string vazia
    sess_empty = await sm.get_or_create_session(session_id="", agent_id="agent_auto")
    assert sess_empty.session_id.startswith("sess_")

    # Teste com espaços em branco
    sess_space = await sm.get_or_create_session(session_id="   ", agent_id="agent_auto")
    assert sess_space.session_id.startswith("sess_")

    # IDs gerados automaticamente devem ser distintos
    assert len({sess_none.session_id, sess_empty.session_id, sess_space.session_id}) == 3


@pytest.mark.asyncio
async def test_get_or_create_session_idempotency_and_trimming() -> None:
    """Valida idempotência na recuperação e tratamento de espaços extras no ID."""
    sm = SessionManager()

    # Criação inicial com espaços ao redor do ID
    sess1 = await sm.get_or_create_session(session_id="  sess_padded_42  ", agent_id="original_agent")
    assert sess1.session_id == "sess_padded_42"

    # Segunda chamada com o mesmo ID (sem espaços) deve retornar a mesma instância
    sess2 = await sm.get_or_create_session(session_id="sess_padded_42", agent_id="new_agent")
    assert sess1 is sess2
    assert sess2.agent_id == "original_agent"  # Mantém agent_id original


@pytest.mark.asyncio
async def test_get_or_create_session_concurrency() -> None:
    """Garante atomicidade e ausência de race conditions sob criação concorrente extrema."""
    sm = SessionManager()
    target_id = "sess_concurrent_lock"

    # Dispara 50 chamadas simultâneas para o mesmo ID
    results = await asyncio.gather(
        *(sm.get_or_create_session(target_id, agent_id=f"worker_{i}") for i in range(50))
    )

    # Todas as corrotinas devem ter retornado a exata mesma instância de AgentSession
    first_session = results[0]
    assert all(s is first_session for s in results)
    assert len(sm._sessions) == 1
