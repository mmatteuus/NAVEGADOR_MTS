"""
Testes de resiliência multi-navegador, multi-agente e reconexão da extensão MV3.

Valida deduplicação de sockets por instanceId, seleção inteligente entre múltiplos
navegadores (Chrome/Edge), limpeza de vínculos órfãos e concessão automática de abas.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from src.mcp.ws_session_registry import WSSessionRegistry

ROOT_DIR = Path(__file__).resolve().parents[1]


class DummySocket:
    """Socket simulado saudável para testes de registro e seleção."""

    def __init__(self, name: str = "sock") -> None:
        self.name = name
        self.closed = False


def test_reconnect_same_instance_replaces_zombie_socket() -> None:
    """Garante que reconexão com mesmo instanceId substitui o socket antigo sem duplicar."""
    reg = WSSessionRegistry()
    sock_old = DummySocket("chrome_old")
    sock_new = DummySocket("chrome_new")

    reg.register_extension(sock_old, {"instanceId": "inst-chrome", "grantedTabIds": [10]})
    assert reg.select_socket("agent-1", 10) is sock_old
    assert len(reg.extension_sockets()) == 1

    # Reconexão do Service Worker trazendo o mesmo instanceId antes do close do socket antigo
    reg.register_extension(sock_new, {"instanceId": "inst-chrome", "grantedTabIds": [10, 11]})
    assert len(reg.extension_sockets()) == 1
    assert reg.extension_sockets()[0] is sock_new
    assert reg.get_active_extension() is sock_new
    assert reg.select_socket("agent-1", 10) is sock_new
    assert reg.select_socket("agent-1", 11) is sock_new


def test_multi_browser_selection_by_open_tabs_and_recency() -> None:
    """Valida desempate multi-navegador por grantedTabIds, openTabIds e lastActivatedAt."""
    reg = WSSessionRegistry()
    chrome = DummySocket("chrome")
    edge = DummySocket("edge")

    reg.register_extension(chrome, {
        "instanceId": "chrome-1",
        "grantedTabIds": [],
        "openTabIds": [101, 102],
        "lastActivatedAt": 1000,
    })
    reg.register_extension(edge, {
        "instanceId": "edge-1",
        "grantedTabIds": [],
        "openTabIds": [201, 202],
        "lastActivatedAt": 2000,
    })

    # Busca por tabId presente em openTabIds roteia para o navegador correto
    assert reg.select_socket("agent-open", 202) is edge
    assert reg.select_socket("agent-chrome", 101) is chrome

    # Sem tabId e ambos sem grants: escolhe o mais recentemente ativado (lastActivatedAt maior)
    assert reg.select_socket("agent-recent", None) is edge

    # Se apenas Chrome possui grantedTabIds e tabId não foi informado, prioriza Chrome
    reg.register_extension(chrome, {
        "instanceId": "chrome-1",
        "grantedTabIds": [101],
        "openTabIds": [101, 102],
        "lastActivatedAt": 1000,
    })
    assert reg.select_socket("agent-granted", None) is chrome


def test_orphan_session_binding_clears_when_browser_closed() -> None:
    """Limpa vínculo órfão quando o navegador vinculado é encerrado e outro está ativo."""
    reg = WSSessionRegistry()
    chrome = DummySocket("chrome")
    edge = DummySocket("edge")

    reg.register_extension(chrome, {"instanceId": "chrome-id", "grantedTabIds": [10]})
    reg.register_extension(edge, {"instanceId": "edge-id", "grantedTabIds": [20]})

    assert reg.select_socket("agent-x", 10) is chrome
    chrome.closed = True
    reg.unregister(chrome)

    # Como o Chrome foi encerrado e desregistrado, agent-x pode migrar para o Edge
    assert reg.select_socket("agent-x", 20) is edge
    assert reg.select_socket("agent-x", None) is edge


def test_extension_constants_and_auto_grant_in_node() -> None:
    """Verifica constantes MV3, auto-concessão de aba criada pelo agente e hello enriquecido."""
    script = """
    import assert from 'node:assert/strict';
    import { PORT_CANDIDATES, MAX_RETRIES_BEFORE_PORT_HOP, KEEP_ALIVE_PERIOD_MINUTES } from './src/extension/common/constants.js';

    assert.equal(PORT_CANDIDATES.includes(3457), false, 'Porta HTTP 3457 não pode estar em PORT_CANDIDATES');
    assert.equal(MAX_RETRIES_BEFORE_PORT_HOP, 5);
    assert.equal(KEEP_ALIVE_PERIOD_MINUTES, 0.4);

    let tabs = [{ id: 50, url: 'https://auto.test', title: 'Auto', active: true, windowId: 1 }];
    let store = {};
    globalThis.WebSocket = class { static OPEN = 1; constructor() { this.readyState = 1; } send() {} close() {} };
    globalThis.chrome = {
      runtime: { getURL: p => `chrome-extension://test/${p}`, getManifest: () => ({ version: '2.3.3' }) },
      storage: {
        local: { get: async k => ({ [k]: store[k] }), set: async v => Object.assign(store, v) },
        session: { get: async k => (k ? { [k]: store[k] } : store), set: async v => Object.assign(store, v) }
      },
      tabs: {
        query: async () => tabs,
        get: async id => tabs.find(t => t.id === Number(id)) || null,
        onRemoved: { addListener() {} }, onReplaced: { addListener() {} }, onActivated: { addListener() {} }
      },
      windows: { onRemoved: { addListener() {} }, onFocusChanged: { addListener() {} } }
    };

    const { createClientHello } = await import('./src/extension/background/extension_identity.js');
    const { targetId, grantAgentTab, grantedTabs } = await import('./src/extension/background/tab_access.js');

    const autoId = await targetId(undefined, 'sess-1');
    assert.equal(autoId, 50, 'Sem restrições prévias, deve auto-conceder a aba ativa');
    tabs.push({ id: 51, url: 'https://new.test', title: 'New', active: true, windowId: 1 });
    await grantAgentTab('sess-1', 51);
    assert.equal(await targetId(undefined, 'sess-1'), 51, 'Deve resolver para a última aba criada pela sessão');
    const hello = await createClientHello(tabs[0]);
    assert.deepEqual(hello.payload.openTabIds, [50, 51]);
    assert.ok(typeof hello.payload.lastActivatedAt === 'number');
    assert.ok((await grantedTabs()).includes(51));
    """
    res = subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT_DIR, capture_output=True, text=True)
    assert res.returncode == 0, f"Falha no teste Node:\n{res.stderr}"
