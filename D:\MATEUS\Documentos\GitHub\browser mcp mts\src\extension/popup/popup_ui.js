/**
 * @file popup_ui.js
 * @description Módulo de manipulação dos elementos visuais do Popup da extensão.
 *
 * Gerencia as transições de cores do LED, textos de latência em tempo real
 * e crachás de autorização do módulo Computer Use.
 */

window.popupUI = (function () {
  const elements = {
    toggle: document.getElementById('automation-toggle'),
    toggleDesc: document.getElementById('toggle-desc'),
    version: document.getElementById('extension-version'),
    updateState: document.getElementById('extension-update-state'),
    led: document.getElementById('status-led'),
    statusText: document.getElementById('status-text'),
    latencyText: document.getElementById('latency-text'),
    commandsText: document.getElementById('commands-text'),
    btnReconnect: document.getElementById('btn-reconnect'),
    portText: document.getElementById('port-text'),
    safetyIcon: document.getElementById('safety-icon'),
    safetyState: document.getElementById('safety-state')
  };

  try {
    const manifest = chrome.runtime.getManifest();
    if (elements.version && manifest?.version) {
      elements.version.textContent = `Automação Web Segura • v${manifest.version}`;
    }
  } catch (_) {
    // O restante do popup continua utilizável se o manifesto não puder ser lido.
  }

  /**
   * Atualiza o indicador luminoso LED e o texto do status da conexão WebSocket.
   * @param {string} status - Estado ('connected', 'reconnecting', 'disconnected').
   * @param {number} [latencyMs=0] - Valor medido de latência em milissegundos.
   */
  function updateConnectionDisplay(status, latencyMs = 0) {
    if (!elements.led || !elements.statusText) return;

    elements.led.className = 'led'; // Reseta classes anteriores

    switch (status) {
      case 'connected':
        elements.led.classList.add('connected');
        elements.statusText.textContent = 'Conectado';
        elements.statusText.style.color = 'var(--led-green)';
        elements.btnReconnect.style.display = 'none';
        elements.latencyText.textContent = `${latencyMs} ms`;
        break;

      case 'reconnecting':
      case 'connecting':
        elements.led.classList.add('reconnecting');
        elements.statusText.textContent = 'Reconectando...';
        elements.statusText.style.color = '#d4a000';
        elements.btnReconnect.style.display = 'none';
        elements.latencyText.textContent = '-- ms';
        break;

      case 'disconnected':
      default:
        elements.statusText.textContent = 'Desconectado';
        elements.statusText.style.color = 'var(--led-red)';
        elements.btnReconnect.style.display = 'block';
        elements.latencyText.textContent = '-- ms';
        break;
    }
  }

  /**
   * Atualiza a posição do interruptor e texto explicativo.
   * @param {boolean} enabled - Se a automação está ativa.
   */
  function updateToggleDisplay(enabled) {
    if (!elements.toggle || !elements.toggleDesc) return;
    elements.toggle.checked = !!enabled;
    elements.toggleDesc.textContent = enabled
      ? 'Agente autorizado a interagir com abas'
      : 'Automação pausada pelo usuário';
  }

  /**
   * Atualiza o indicador do módulo de controle do sistema operacional (Computer Use).
   * @param {boolean} allowed - Se o controle do computador está autorizado.
   */
  function updateSafetyDisplay(allowed) {
    if (!elements.safetyIcon || !elements.safetyState) return;
    if (allowed) {
      elements.safetyIcon.textContent = '🟢';
      elements.safetyState.textContent = 'Autorizado (Pressione ESC 3x para parar)';
      elements.safetyState.style.color = 'var(--led-green)';
    } else {
      elements.safetyIcon.textContent = '🛡️';
      elements.safetyState.textContent = 'Bloqueado (Somente controle de abas web)';
      elements.safetyState.style.color = 'var(--text-secondary)';
    }
  }

  /**
   * Atualiza a contagem de comandos processados.
   * @param {number} count - Total de comandos executados.
   */
  function updateCommandsCount(count) {
    if (elements.commandsText) {
      elements.commandsText.textContent = `${count || 0} executados`;
    }
  }

  /**
   * Atualiza o endereço da porta local ativa.
   * @param {number} port - Número da porta.
   */
  function updatePortDisplay(port) {
    if (elements.portText && port) {
      elements.portText.textContent = `ws://127.0.0.1:${port}`;
    }
  }
  function updateExtensionUpdateState(state = {}) {
    if (!elements.updateState) return;
    const labels = { pending: 'Atualização aguardando comandos', reloading: 'Recarregando extensão...',
      confirmed: 'Extensão atualizada', error: `Atualização: ${state.error || 'verificação necessária'}` };
    elements.updateState.textContent = labels[state.status] || '';
  }

  return {
    elements,
    updateConnectionDisplay,
    updateToggleDisplay,
    updateSafetyDisplay,
    updateCommandsCount,
    updatePortDisplay,
    updateExtensionUpdateState
  };
})();
