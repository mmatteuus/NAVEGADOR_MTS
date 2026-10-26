"""Testes Unitários de Segurança e Configuração do BROWSER MTS."""

from __future__ import annotations

import base64
import ctypes
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

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

    def test_encrypt_dpapi_non_windows_platform_raises_security_error(self) -> None:
        """Garante que encrypt_dpapi rejeita execução em sistemas não-Windows."""
        with patch("sys.platform", "linux"):
            with self.assertRaises(SecurityError) as ctx:
                encrypt_dpapi("chave-secreta")
            self.assertIn("DPAPI só é suportada nativamente", str(ctx.exception))

    def test_encrypt_dpapi_empty_input_raises_value_error(self) -> None:
        """Valida que entradas vazias lançam exceção explicativa."""
        with patch("sys.platform", "win32"):
            with self.assertRaises(ValueError):
                encrypt_dpapi("")
            with self.assertRaises(ValueError):
                encrypt_dpapi(b"")

    def test_encrypt_dpapi_str_and_bytes_success(self) -> None:
        """Valida criptografia DPAPI bem-sucedida para str e bytes com liberador de memória."""
        mock_c32, mock_k32 = MagicMock(), MagicMock()
        mock_c32.CryptProtectData.return_value = 1
        with patch("sys.platform", "win32"), \
             patch.object(ctypes, "windll", create=True) as m_windll, \
             patch("ctypes.string_at", return_value=b"encrypted_payload") as m_str_at:
            m_windll.crypt32, m_windll.kernel32 = mock_c32, mock_k32
            res_str = encrypt_dpapi("texto_puro", description="MeuApp")
            expected_b64 = base64.b64encode(b"encrypted_payload").decode("ascii")
            self.assertEqual(res_str, expected_b64)
            res_bytes = encrypt_dpapi(b"bytes_puros")
            self.assertEqual(res_bytes, expected_b64)
            mock_k32.LocalFree.assert_called()
            m_str_at.assert_called()

    def test_dpapi_encrypt_decrypt_roundtrip(self) -> None:
        """Garante que a DPAPI criptografa e restaura o dado original no Windows."""
        secreto = "sk-proj-teste-real-de-credencial-1234567890"
        if sys.platform != "win32":
            with patch("sys.platform", "linux"):
                with self.assertRaises(SecurityError):
                    encrypt_dpapi(secreto)
            return
        cifrado = encrypt_dpapi(secreto)
        self.assertNotEqual(secreto, cifrado)
        self.assertEqual(secreto, decrypt_dpapi(cifrado))

    def test_mask_credential_variations(self) -> None:
        """Testa diferentes formatos de chave no mascaramento para tela."""
        self.assertEqual(mask_credential(None), "[NÃO CONFIGURADO]")
        self.assertEqual(mask_credential(""), "[NÃO CONFIGURADO]")
        self.assertEqual(mask_credential("   "), "[NÃO CONFIGURADO]")
        self.assertEqual(mask_credential("123"), "•••")
        chave_sk = "sk-proj-abcdef1234567890xyz"
        mascara_sk = mask_credential(chave_sk, visible_tail=4)
        self.assertTrue(mascara_sk.startswith("sk-•") and mascara_sk.endswith("0xyz"))

    def test_sanitize_log_masks_sensitive_patterns(self) -> None:
        """Verifica se chaves e segredos em strings de log são higienizados."""
        texto_sujo = "Erro sk-proj-1234567890abcdef1234 no túnel tunnel_6a7aea545c408191889cd114d4a99d9b"
        limpo = sanitize_log(texto_sujo)
        self.assertNotIn("sk-proj-1234567890abcdef1234", limpo)
        self.assertIn("sk-****[MASCARADO]****", limpo)


class TestConfigModule(unittest.TestCase):
    """Suíte de validação de portas e diretórios de configuração."""

    def test_default_config_values(self) -> None:
        """Garante que a porta padrão seja 3456."""
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
        self.assertEqual(config.credentials_file, config.secrets_dir / "runtime_key.enc")

    def test_secrets_dir_creation_on_disk(self) -> None:
        """Valida que ensure_directories cria secrets_dir em disco de forma isolada."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_app_data = Path(tmp_dir) / "app_data"
            config = AppConfig(app_data_dir=temp_app_data)
            self.assertFalse(config.secrets_dir.exists())
            config.ensure_directories()
            self.assertTrue(config.secrets_dir.is_dir())

    def test_env_var_override(self) -> None:
        """Verifica se variáveis de ambiente sobrescrevem os padrões corretamente."""
        os.environ["BROWSER_MTS_PORT"] = "3888"
        try:
            cfg = load_config()
            self.assertEqual(cfg.port, 3888)
        finally:
            os.environ.pop("BROWSER_MTS_PORT", None)


if __name__ == "__main__":
    unittest.main()
