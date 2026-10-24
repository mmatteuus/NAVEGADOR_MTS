## 2024-10-24 - Exception handling inside hot path optimization
**Learning:** In the `ws_session_registry.py`, `is_socket_healthy` was capturing an exception every time it tried to access the state due to an import attempt inside the exception handling. Caching the imported value speeds up the process significantly because we avoid throwing exceptions frequently.
**Action:** Always verify if try/except blocks inside hot loops or frequently called functions can be substituted with checks or by caching values ahead of time to avoid exception handling overhead.
