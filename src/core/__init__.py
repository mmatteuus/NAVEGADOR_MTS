"""Pacote Core do BROWSER MTS.

Módulos fundamentais:
- security: Criptografia Windows DPAPI, higienização de logs e máscaras de UI.
- config: Centralização de portas de rede (porta 3456), diretórios e configurações.
"""

from src.core.config import (
    AppConfig,
    current_config,
    load_config,
)
from src.core.security import (
    SecurityError,
    decrypt_dpapi,
    encrypt_dpapi,
    mask_credential,
    sanitize_log,
)
from src.core.updater import (
    APP_VERSION,
    UpdateInfo,
    check_for_updates,
    download_and_launch_update,
)

__all__ = [
    "AppConfig",
    "load_config",
    "current_config",
    "encrypt_dpapi",
    "decrypt_dpapi",
    "mask_credential",
    "sanitize_log",
    "SecurityError",
    "APP_VERSION",
    "UpdateInfo",
    "check_for_updates",
    "download_and_launch_update",
]
