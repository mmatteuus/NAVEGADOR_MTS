/**
 * @file popup.js
 * @description Controlador e orquestrador de eventos da janela Popup do BROWSER MTS.
 * 
 * Sincroniza o estado em tempo real com o Service Worker, reage a mudanças
 * no storage e captura ações do usuário no interruptor de automação.
 */

document.addEventListener('DOMContentLoaded', () => {
  const ui = window.popupUI;

  // 1. Carrega o estado atual a partir do Service Worker
  chrome.runtime.sendMessage({ type: 'GET_POPUP_STATE' }, (response) => {
    if (chrome.runtime.lastError || !response || !response.success) {
      console.warn('[Popup] Não foi possível obter estado inicial do worker:', chrome.runtime.lastError);
      return;
    }

    const { automationEnabled, connectionStatus, latencyMs, computerUseAllowed, totalCommands, activePort, updateState } = response.data;
    ui.updateToggleDisplay(automationEnabled);
    ui.updateConnectionDisplay(connectionStatus, latencyMs);
    ui.updateSafetyDisplay(computerUseAllowed);
    ui.updateCommandsCount(totalCommands);
    if (activePort) ui.updatePortDisplay(activePort);
    ui.updateExtensionUpdateState(updateState);
  });

  // 2. Manipula o clique no interruptor de automação
  if (ui.elements.toggle) {
    ui.elements.toggle.addEventListener('change', (e) => {
      const isChecked = e.target.checked;
      ui.updateToggleDisplay(isChecked);

      chrome.runtime.sendMessage({ type: 'TOGGLE_AUTOMATION', enabled: isChecked }, (response) => {
        if (!response?.success) ui.updateToggleDisplay(false);
        else ui.updateToggleDisplay(response.enabled);
        if (response?.success && !response.enabled) {
          ui.updateConnectionDisplay('disconnected', 0);
        }
      });
    });
  }

  // 3. Botão de reconexão manual imediata
  if (ui.elements.btnReconnect) {
    ui.elements.btnReconnect.addEventListener('click', () => {
      ui.updateConnectionDisplay('reconnecting', 0);
      chrome.runtime.sendMessage({ type: 'RECONNECT_NOW' });
    });
  }

  // 4. Observa alterações de estado em tempo real via storage
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local') return;

    if (changes.browser_mts_connection_status || changes.browser_mts_last_latency_ms) {
      chrome.storage.local.get(['browser_mts_connection_status', 'browser_mts_last_latency_ms'], (data) => {
        ui.updateConnectionDisplay(data.browser_mts_connection_status, data.browser_mts_last_latency_ms);
      });
    }

    if (changes.browser_mts_automation_enabled) {
      ui.updateToggleDisplay(changes.browser_mts_automation_enabled.newValue);
    }

    if (changes.browser_mts_computer_use_allowed) {
      ui.updateSafetyDisplay(changes.browser_mts_computer_use_allowed.newValue);
    }

    if (changes.browser_mts_total_commands) {
      ui.updateCommandsCount(changes.browser_mts_total_commands.newValue);
    }

    if (changes.browser_mts_active_port) {
      ui.updatePortDisplay(changes.browser_mts_active_port.newValue);
    }
    if (changes.browser_mts_extension_update_state) {
      ui.updateExtensionUpdateState(changes.browser_mts_extension_update_state.newValue);
    }
  });
});
