/**
 * @file mcp_agent_client.mjs
 * @description Cliente JSON-RPC HTTP Streamable para conexão de agentes com o
 * servidor MCP e gerenciamento estrito de sessões isoladas (Mcp-Session-Id).
 */

export class MCPAgentClient {
  constructor(baseUrl, sessionId) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.sessionId = sessionId;
    this.reqCounter = 0;
    this.initialized = false;
  }

  async sendJsonRpc(method, params = {}) {
    const reqId = `${this.sessionId}_${++this.reqCounter}`;
    const payload = {
      jsonrpc: '2.0',
      id: reqId,
      method,
      params
    };

    const res = await fetch(`${this.baseUrl}/mcp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Mcp-Session-Id': this.sessionId
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status} de ${this.baseUrl}/mcp: ${errText}`);
    }

    return res.json();
  }

  async initialize() {
    const resp = await this.sendJsonRpc('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: `Agent_${this.sessionId}`, version: '1.0.0' }
    });

    if (resp.error) {
      throw new Error(`Falha no initialize: ${JSON.stringify(resp.error)}`);
    }

    this.initialized = true;
    return resp.result;
  }

  async listTools() {
    const resp = await this.sendJsonRpc('tools/list', {});
    if (resp.error) throw new Error(resp.error.message || 'Erro ao listar ferramentas');
    return resp.result?.tools || [];
  }

  async callTool(name, args = {}) {
    const resp = await this.sendJsonRpc('tools/call', {
      name,
      arguments: args
    });

    if (resp.error) {
      return { isError: true, error: resp.error.message || 'Erro JSON-RPC', raw: resp };
    }

    const result = resp.result;
    if (result && result.isError === true) {
      const text = result.content?.find(c => c.type === 'text')?.text || 'Erro desconhecido';
      return { isError: true, error: text, content: result.content };
    }

    const textItem = result?.content?.find(c => c.type === 'text');
    let parsedData = null;
    if (textItem && typeof textItem.text === 'string') {
      try {
        parsedData = JSON.parse(textItem.text);
      } catch (_) {
        parsedData = textItem.text;
      }
    }

    return {
      isError: false,
      data: parsedData,
      content: result?.content,
      raw: result
    };
  }
}
