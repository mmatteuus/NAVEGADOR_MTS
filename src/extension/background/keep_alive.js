/**
 * @file keep_alive.js
 * @description Mecanismo triplo contra a suspensão do Service Worker no Manifest V3.
 * 
 * O Chromium suspende Service Workers inativos após 30 segundos. Este módulo
 * emprega alarmes nativos a cada 20s, ping-pong de transporte e escuta de eventos
 * para manter o worker ativo e reatar a conexão sempre que necessário.
 */

import { KEEP_ALIVE_ALARM_NAME, KEEP_ALIVE_PERIOD_MINUTES } from '../common/constants.js';
import { logger } from '../common/logger.js';

let healthCheckCallback = null;

/**
 * Inicializa a estratégia de persistência e alarme contínuo.
 * @param {Function} onPulseCheck - Função chamada a cada ciclo para checar a conexão.
 */
export function initKeepAlive(onPulseCheck) {
  healthCheckCallback = onPulseCheck;

  // 1. Cria ou recria o alarme periódico nativo de 20 segundos
  chrome.alarms.get(KEEP_ALIVE_ALARM_NAME, (existingAlarm) => {
    if (!existingAlarm) {
      chrome.alarms.create(KEEP_ALIVE_ALARM_NAME, {
        periodInMinutes: KEEP_ALIVE_PERIOD_MINUTES
      });
      logger.info(`Alarme keep-alive agendado a cada ${KEEP_ALIVE_PERIOD_MINUTES * 60}s.`);
    }
  });

  // 2. Escuta os disparos periódicos do alarme
  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === KEEP_ALIVE_ALARM_NAME) {
      logger.debug('Pulso de alarme keep-alive recebido. Service worker desperto.');
      if (typeof healthCheckCallback === 'function') {
        healthCheckCallback();
      }
    }
  });

  // 3. Acorda e revalida ao trocar de aba no navegador
  chrome.tabs.onActivated.addListener((activeInfo) => {
    logger.debug(`Aba alterada para ID ${activeInfo.tabId}. Verificando prontidão.`);
    if (typeof healthCheckCallback === 'function') {
      healthCheckCallback();
    }
  });

  // 4. Acorda quando nova navegação for confirmada
  if (chrome.webNavigation && chrome.webNavigation.onCommitted) {
    chrome.webNavigation.onCommitted.addListener(() => {
      if (typeof healthCheckCallback === 'function') {
        healthCheckCallback();
      }
    });
  }

  logger.info('Estratégia tripla keep-alive armada com sucesso.');
}

/**
 * Força um pulso imediato de verificação do keep-alive.
 */
export function triggerPulse() {
  if (typeof healthCheckCallback === 'function') {
    healthCheckCallback();
  }
}
