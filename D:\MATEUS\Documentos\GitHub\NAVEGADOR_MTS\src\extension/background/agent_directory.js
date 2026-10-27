/** Diretório efêmero de agentes anunciado pelo Desktop App. */
let agents = [];

function normalize(value) {
  if (!value || typeof value !== 'object' || !value.sessionId) return null;
  return {
    sessionId: String(value.sessionId),
    agentId: value.agentId ? String(value.agentId) : '',
    lastActivity: Number(value.lastActivity) || 0,
    connected: value.connected !== false
  };
}

export function setAgentDirectory(next) {
  agents = Array.isArray(next) ? next.map(normalize).filter(Boolean) : [];
  return getAgentDirectory();
}

export function getAgentDirectory() {
  return agents.map(agent => ({ ...agent }));
}

export function clearAgentDirectory() { agents = []; }
