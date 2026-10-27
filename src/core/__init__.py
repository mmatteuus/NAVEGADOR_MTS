"""Pacote Core do BROWSER MTS.

Módulos fundamentais:
- security: Criptografia Windows DPAPI, higienização de logs e máscaras de UI.
- config: Centralização de portas de rede (porta 3456), diretórios e configurações.
"""

from src.core.config import (
    AppConfig as AppConfig,
    load_config as load_config,
)
from src.core.security import (
    SecurityError as SecurityError,
    decrypt_dpapi as decrypt_dpapi,
    encrypt_dpapi as encrypt_dpapi,
    mask_credential as mask_credential,
    sanitize_log as sanitize_log,
)
from src.core.updater import (
    APP_VERSION as APP_VERSION,
    UpdateInfo as UpdateInfo,
    check_for_updates as check_for_updates,
    download_and_launch_update as download_and_launch_update,
)

__all__ = [
    "AppConfig",
    "load_config",
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
