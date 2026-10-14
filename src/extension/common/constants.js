/**
 * @file constants.js
 * @description Constantes centrais de configuração da extensão Browser MTS.
 * 
 * Centraliza endereços, intervalos de tempo do ciclo de vida, limites
 * de backoff exponencial e identificadores dos comandos suportados.
 */

/** Endereço do WebSocket Bridge hospedado pelo Desktop App Windows */
export const WS_URL = 'ws://127.0.0.1:3456';

/** Intervalo do Heartbeat de transporte em milissegundos (3 segundos) */
export const HEARTBEAT_INTERVAL_MS = 3000;

/** Limite de tolerância para pings sem resposta antes de declarar queda (6 segundos) */
export const HEARTBEAT_TIMEOUT_MS = 6000;

/** Nome do alarme nativo para evitar suspensão de 30s do Service Worker MV3 */
export const KEEP_ALIVE_ALARM_NAME = 'browser_mts_keep_alive';

/** Período do alarme em minutos (0.33 minutos = aproximadamente 20 segundos) */
export const KEEP_ALIVE_PERIOD_MINUTES = 0.33;

/** Etapas do Backoff Exponencial para reconexão ao Desktop App (em milissegundos) */
export const RECONNECT_BACKOFF_STEPS_MS = [500, 1000, 2000, 5000];

/** Chave de armazenamento das preferências do usuário no chrome.storage.local */
export const STORAGE_KEYS = {
  AUTOMATION_ENABLED: 'browser_mts_automation_enabled',
  LAST_LATENCY_MS: 'browser_mts_last_latency_ms',
  CONNECTION_STATUS: 'browser_mts_connection_status',
  COMPUTER_USE_ALLOWED: 'browser_mts_computer_use_allowed',
  TOTAL_COMMANDS: 'browser_mts_total_commands'
};

/** Estados possíveis de conectividade da extensão */
export const CONNECTION_STATE = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting'
};

/** Ações suportadas de controle de abas e navegação */
export const TAB_ACTIONS = [
  'browser_navigate',
  'browser_new_tab',
  'browser_close_tab',
  'browser_switch_tab',
  'browser_list_tabs',
  'browser_go_back',
  'browser_go_forward'
];

/** Ações de interação e inspeção web encaminhadas ao Content Script */
export const CONTENT_ACTIONS = [
  'browser_click',
  'browser_type',
  'browser_hover',
  'browser_select',
  'browser_select_option',
  'browser_press_key',
  'browser_scroll',
  'browser_get_dom',
  'browser_get_text',
  'browser_find_elements',
  'browser_evaluate_js',
  'browser_snapshot'
];
