"""Duas raizes reais e sessoes MCP concorrentes, sem dados pessoais."""
from __future__ import annotations
import asyncio
import json
import pytest
from src.computer.folder_assignments import folder_grants
from src.computer.safety_gate import safety_gate
from src.mcp.computer_dispatch import execute_mcp_computer
from src.mcp.router import MCPToolRouter


@pytest.mark.asyncio
async def test_concurrent_folders_remain_isolated_through_router(tmp_path, reset_safety_gate):
    """Leitura/escrita simultaneas nunca misturam roots nem versoes de outro agente."""
    folder_grants.clear()
    safety_gate.authorize()
    paths = {sid: tmp_path / sid for sid in ('agent-a', 'agent-b')}
    for path in paths.values():
        path.mkdir()
    grants = {sid: folder_grants.assign(sid, path) for sid, path in paths.items()}
    router = MCPToolRouter(computer_executor=execute_mcp_computer,
                           safety_checker=safety_gate.is_authorized)

    async def raw(sid, operation, **params):
        return await router.dispatch('computer_folder_action',
            {'operation': operation, **params}, session_id=sid)

    async def call(sid, operation, **params):
        response = await raw(sid, operation, rootId=grants[sid].root_id, **params)
        assert not response['isError'], response
        return json.loads(response['content'][0]['text'])

    async def scenario(sid):
        visible = await call(sid, 'list_roots')
        assert [root['rootId'] for root in visible['roots']] == [grants[sid].root_id]
        await call(sid, 'create', path='texto.txt', content=f'{sid}:0')
        for step in range(1, 4):
            read = await call(sid, 'read', path='texto.txt')
            assert read['content'] == f'{sid}:{step - 1}'
            await call(sid, 'write', path='texto.txt', content=f'{sid}:{step}',
                       expectedVersion=read['version'])
        listing = await call(sid, 'list')
        assert [item['name'] for item in listing['entries']] == ['texto.txt']

    try:
        await asyncio.gather(*(scenario(sid) for sid in paths))
        for sid, path in paths.items():
            assert path.joinpath('texto.txt').read_text(encoding='utf-8') == f'{sid}:3'
        denied = await raw('agent-a', 'create', rootId=grants['agent-b'].root_id,
                           path='intrusao.txt', content='forbidden')
        assert denied['isError'] and 'FOLDER_NOT_ASSIGNED' in denied['content'][0]['text']
        assert not paths['agent-b'].joinpath('intrusao.txt').exists()
        forged = await raw('agent-a', 'list_roots', sessionId='agent-b')
        assert forged['isError'] and 'forja' in forged['content'][0]['text'].lower()
        folder_grants.revoke('agent-a')
        late = await raw('agent-a', 'create', rootId=grants['agent-a'].root_id,
                         path='revogado.txt', content='forbidden')
        assert late['isError'] and not paths['agent-a'].joinpath('revogado.txt').exists()
        assert (await call('agent-b', 'read', path='texto.txt'))['content'] == 'agent-b:3'
    finally:
        folder_grants.clear()