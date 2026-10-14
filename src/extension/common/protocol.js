/**
 * @file protocol.js
 * @description Construtor de envelopes do protocolo WebSocket entre Extensão e Desktop App.
 * 
 * Garante total compatibilidade com o formato esperado pelo Servidor MCP Unificado
 * e pelo ecossistema legado, permitindo rastreabilidade por identificador de requisição.
 */

/**
 * Cria a mensagem inicial de handshake (client_hello).
 * @param {object} [activeTabInfo=null] - Informações da aba ativa atual.
 * @returns {object} Envelope de apresentação estruturado.
 */
export function buildClientHello(activeTabInfo = null) {
  return {
    type: 'client_hello',
    payload: {
      client: 'browser_mts_extension',
      version: '2.0.0',
      browser: 'Chromium / Manifest V3',
      timestamp: Date.now(),
      activeTab: activeTabInfo
    }
  };
}

/**
 * Constrói envelope de resposta a comando para o Desktop App / Servidor MCP.
 * Suporta o padrão duplo: messageResponse (legado/MCP) e browser_response (novo).
 * 
 * @param {string} requestId - Identificador único da requisição original.
 * @param {boolean} success - Se a operação teve êxito.
 * @param {any} [data=null] - Dados retornados pela ação executada.
 * @param {string|null} [errorMessage=null] - Descrição amigável da falha se houver.
 * @returns {object} Mensagem estruturada para envio via WebSocket.
 */
export function buildActionResponse(requestId, success, data = null, errorMessage = null) {
  return {
    id: requestId,
    type: 'messageResponse',
    success,
    payload: {
      requestId,
      result: success ? data : null,
      error: errorMessage
    },
    data: success ? data : null,
    error: errorMessage,
    timestamp: Date.now()
  };
}

/**
 * Cria mensagem de pulso Heartbeat Pong em resposta ao Ping do servidor.
 * 
 * @param {number} serverTs - Carimbo de data/hora enviado pelo servidor.
 * @returns {object} Envelope pong com timestamp do cliente.
 */
export function buildHeartbeatPong(serverTs) {
  return {
    type: 'pong',
    ts: serverTs,
    clientTs: Date.now()
  };
}

/**
 * Constrói pulso ativo de Ping originado pelo cliente para verificação periódica.
 * @returns {object} Envelope ping com timestamp atual.
 */
export function buildHeartbeatPing() {
  return {
    type: 'ping',
    ts: Date.now()
  };
}
