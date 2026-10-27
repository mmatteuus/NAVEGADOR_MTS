import { PORT_CANDIDATES, MAX_RETRIES_BEFORE_PORT_HOP, STORAGE_KEYS } from '../common/constants.js';

export function createPortRecovery() {
  let preferredIndex = 0;
  let currentIndex = 0;
  let alternateIndex = 0;
  let retries = 0;
  let loaded = false;

  return {
    async load() {
      if (loaded) return;
      loaded = true;
      try {
        const data = await chrome.storage.local.get(STORAGE_KEYS.ACTIVE_PORT);
        const saved = PORT_CANDIDATES.indexOf(Number(data[STORAGE_KEYS.ACTIVE_PORT]));
        preferredIndex = saved >= 0 ? saved : 0;
      } catch (_) { preferredIndex = 0; }
      currentIndex = preferredIndex;
      alternateIndex = preferredIndex;
    },
    currentPort() { return PORT_CANDIDATES[currentIndex]; },
    markSuccess() { preferredIndex = currentIndex; retries = 0; },
    advance() {
      if (currentIndex !== preferredIndex) {
        currentIndex = preferredIndex;
        retries = 0;
        return;
      }
      retries++;
      if (retries >= MAX_RETRIES_BEFORE_PORT_HOP) {
        if (currentIndex === preferredIndex) {
          alternateIndex = (alternateIndex + 1) % PORT_CANDIDATES.length;
          if (alternateIndex === preferredIndex) {
            alternateIndex = (alternateIndex + 1) % PORT_CANDIDATES.length;
          }
          currentIndex = alternateIndex;
        } else {
          currentIndex = preferredIndex;
        }
        retries = 0;
      }
    }
  };
}
