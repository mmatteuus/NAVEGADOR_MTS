## 2026-10-25 - Extension Popup Keyboard & Screen Reader Accessibility
**Learning:** Chrome Extension Manifest V3 popups require explicit `:focus-visible` styling and `aria-live="polite"` regions for dynamic status elements to properly announce WebSocket connection changes and tab permission grants to screen readers.
**Action:** Always attach `aria-live="polite"` to dynamic status spans and add explicit `:focus-visible` focus rings in popup CSS when building extension popups.
