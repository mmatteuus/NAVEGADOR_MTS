"""Testes Unitários de Segurança e Configuração do BROWSER MTS.

Validações:
- Criptografia e descriptografia real via Windows DPAPI.
- Mascaramento seguro de credenciais para UI.
- Sanitização de logs contra vazamento de chaves sk-* e tunnel IDs.
- Configurações centralizadas, leitura de portas e diretório secrets_dir.
"""

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import AppConfig, load_config
from src.core.security import (
    SecurityError,
    decrypt_dpapi,
    encrypt_dpapi,
    mask_credential,
    sanitize_log,
)


class TestSecurityModule(unittest.TestCase):
    """Suíte de validação de criptografia e sanitização."""

    @unittest.skipUnless(sys.platform == "win32", "DPAPI requer Windows")
    def test_dpapi_encrypt_decrypt_roundtrip(self) -> None:
        """Garante que a DPAPI criptografa e restaura o dado original fielmente."""
        secreto = "sk-proj-teste-real-de-credencial-1234567890"
        cifrado = encrypt_dpapi(secreto)
        self.assertNotEqual(secreto, cifrado)
        self.assertTrue(len(cifrado) > 20)

        restaurado = decrypt_dpapi(cifrado)
        self.assertEqual(secreto, restaurado)

    @unittest.skipUnless(sys.platform == "win32", "DPAPI requer Windows")
    def test_dpapi_empty_input_raises_value_error(self) -> None:
        """Valida que entradas vazias lançam exceção explicativa."""
        with self.assertRaises(ValueError):
            encrypt_dpapi("")

        with self.assertRaises(ValueError):
            decrypt_dpapi("")

    def test_mask_credential_variations(self) -> None:
        """Testa diferentes formatos de chave no mascaramento para tela."""
        self.assertEqual(mask_credential(None), "[NÃO CONFIGURADO]")
        self.assertEqual(mask_credential(""), "[NÃO CONFIGURADO]")
        self.assertEqual(mask_credential("   "), "[NÃO CONFIGURADO]")
        self.assertEqual(mask_credential("123"), "•••")

        chave_sk = "sk-proj-abcdef1234567890xyz"
        mascara_sk = mask_credential(chave_sk, visible_tail=4)
        self.assertTrue(mascara_sk.startswith("sk-•"))
        self.assertTrue(mascara_sk.endswith("0xyz"))
        self.assertNotIn("abcdef123456789", mascara_sk)

    def test_sanitize_log_masks_sensitive_patterns(self) -> None:
        """Verifica se chaves e segredos em strings de log são higienizados."""
        texto_sujo = (
            "Erro ao conectar com a chave sk-proj-1234567890abcdef1234 no túnel "
            "tunnel_6a7aea545c408191889cd114d4a99d9b com Bearer eyJhbGciOiJIUzI1Ni. "
            "Hash interno: a1b2c3d4e5f678901234567890abcdef"
        )
        limpo = sanitize_log(texto_sujo)
        self.assertNotIn("sk-proj-1234567890abcdef1234", limpo)
        self.assertNotIn("tunnel_6a7aea545c408191889cd114d4a99d9b", limpo)
        self.assertIn("sk-****[MASCARADO]****", limpo)
        self.assertIn("tunnel_****[MASCARADO]****", limpo)
        self.assertIn("Bearer [TOKEN_MASCARADO]", limpo)


class TestConfigModule(unittest.TestCase):
    """Suíte de validação de portas e diretórios de configuração."""

    def test_default_config_values(self) -> None:
        """Garante que a porta de desenvolvimento padrão seja 3456."""
        config = AppConfig()
        self.assertEqual(config.port, 3456)
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.mcp_port, 3457)
        self.assertTrue(str(config.secrets_dir).endswith("secrets"))

    def test_secrets_dir_property_and_credentials_path(self) -> None:
        """Garante o cálculo correto de secrets_dir e credentials_file."""
        custom_app_dir = Path("/tmp/browser-mcp-test")
        config = AppConfig(app_data_dir=custom_app_dir)
        self.assertIsInstance(config.secrets_dir, Path)
        self.assertEqual(config.secrets_dir, custom_app_dir / "secrets")
        self.assertEqual(config.secrets_dir.name, "secrets")
        self.assertEqual(config.credentials_file, config.secrets_dir / "runtime_key.enc")

    def test_secrets_dir_creation_on_disk(self) -> None:
        """Valida que ensure_directories cria secrets_dir em disco de forma isolada."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_app_data = Path(tmp_dir) / "app_data"
            config = AppConfig(app_data_dir=temp_app_data)
            self.assertFalse(config.secrets_dir.exists())
            config.ensure_directories()
            self.assertTrue(config.secrets_dir.exists())
            self.assertTrue(config.secrets_dir.is_dir())

    def test_env_var_override(self) -> None:
        """Verifica se variáveis de ambiente sobrescrevem os padrões corretamente."""
        os.environ["BROWSER_MTS_PORT"] = "3888"
        os.environ["BROWSER_MTS_DEV_MODE"] = "1"
        try:
            cfg = load_config()
            self.assertEqual(cfg.port, 3888)
            self.assertTrue(cfg.dev_mode)
        finally:
            os.environ.pop("BROWSER_MTS_PORT", None)
            os.environ.pop("BROWSER_MTS_DEV_MODE", None)


if __name__ == "__main__":
    unittest.main()
