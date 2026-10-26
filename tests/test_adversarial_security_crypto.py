"""Testes Adversariais de Criptografia DPAPI, Mascaramento e Sanitização de Logs.

Validações rigorosas de segurança da informação:
- Integridade da DPAPI com Unicode, emojis, payloads grandes e dados corrompidos.
- Mascaramento visual em UI contra vazamento de caracteres em qualquer tamanho.
- Sanitização regex contra padrões de chaves sk-*, tunnel IDs, Bearer e hashes hex.
"""

from __future__ import annotations
import base64
import ctypes
import sys
from unittest.mock import MagicMock, patch
import pytest
from src.core.security import (
    encrypt_dpapi, decrypt_dpapi, mask_credential, sanitize_log, SecurityError
)


def test_adversarial_dpapi_unicode_and_large_payloads():
    """Garante fidelidade de dados da DPAPI com Unicode, acentos e payloads grandes."""
    segredo_complexo = "Chave-Segura: 🔐 sk-proj-áéíóú-çãõ-1234567890-§©®"
    payload_grande = "A" * 32768 + "sk-fim-de-payload"

    if sys.platform != "win32":
        mock_c32, mock_k32 = MagicMock(), MagicMock()
        mock_c32.CryptProtectData.return_value = 1

        with patch("sys.platform", "win32"), \
             patch.object(ctypes, "windll", create=True) as m_windll, \
             patch("ctypes.string_at", return_value=b"encrypted_blob"):
            m_windll.crypt32, m_windll.kernel32 = mock_c32, mock_k32

            cifrado_unicode = encrypt_dpapi(segredo_complexo, description="UnicodeTest")
            assert isinstance(cifrado_unicode, str) and len(cifrado_unicode) > 0

            cifrado_grande = encrypt_dpapi(payload_grande)
            assert isinstance(cifrado_grande, str)
            assert m_windll.kernel32.LocalFree.call_count >= 2
        return

    cifrado = encrypt_dpapi(segredo_complexo)
    assert decrypt_dpapi(cifrado) == segredo_complexo

    cifrado_grande = encrypt_dpapi(payload_grande)
    assert decrypt_dpapi(cifrado_grande) == payload_grande


def test_adversarial_dpapi_corrupted_and_tampered_payloads():
    """Valida rejeição segura de payloads corrompidos, vazios ou adulterados."""
    if sys.platform != "win32":
        with pytest.raises(SecurityError) as exc_info:
            encrypt_dpapi("segredo")
        assert "DPAPI só é suportada nativamente" in str(exc_info.value)

        with patch("sys.platform", "win32"):
            with pytest.raises(ValueError):
                encrypt_dpapi("")
            with pytest.raises(ValueError):
                encrypt_dpapi(b"")
            with pytest.raises(ValueError):
                decrypt_dpapi("")
            with pytest.raises(ValueError):
                decrypt_dpapi("not-a-valid-base64-string!!@@")
        return

    with pytest.raises(ValueError):
        encrypt_dpapi("")
    with pytest.raises(ValueError):
        decrypt_dpapi("")
    with pytest.raises(ValueError):
        decrypt_dpapi("not-a-valid-base64-string!!@@")

    cifrado = encrypt_dpapi("segredo-valido-12345")
    raw = bytearray(base64.b64decode(cifrado))
    raw[-10] ^= 0xFF
    adulterado_b64 = base64.b64encode(raw).decode("ascii")

    with pytest.raises(SecurityError):
        decrypt_dpapi(adulterado_b64)


def test_adversarial_mask_credential_boundaries():
    """Testa o mascaramento para UI em múltiplos comprimentos e formatos."""
    assert mask_credential(None) == "[NÃO CONFIGURADO]"
    assert mask_credential("") == "[NÃO CONFIGURADO]"
    assert mask_credential("   ") == "[NÃO CONFIGURADO]"
    assert mask_credential("x") == "•"
    assert mask_credential("1234") == "••••"

    sk_key = "sk-proj-super-secreta-1234567890-final"
    mascarado_sk = mask_credential(sk_key, visible_tail=5)
    assert mascarado_sk.startswith("sk-") and mascarado_sk.endswith("final")
    assert "super-secreta-1234567890" not in mascarado_sk

    generica = "minha-chave-de-api-secreta-9999"
    mascarado_gen = mask_credential(generica, visible_tail=4)
    assert mascarado_gen.endswith("9999")
    assert "api-secreta" not in mascarado_gen


def test_adversarial_sanitize_log_evasion_attempts():
    """Valida sanitização de logs contra formatos diversos e tentativas de evasão."""
    tokens = [
        "sk-proj-1234567890abcdef1234",
        "sk-ant-api03-abcdefghijklmnop12345",
        "sk-abcdefghijklmnopqrstuvwxyz",
        "tunnel_6a7aea545c408191889cd114d4a99d9b",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "a1b2c3d4e5f678901234567890abcdef",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ]
    log_composto = f"""
    [CRITICAL] Request payload: {{"key": "{tokens[0]}", "t": "{tokens[3]}"}}
    [DEBUG] Header: Authorization: {tokens[4]}
    [TRACE] Hash validation error for {tokens[5]} and sha256 {tokens[6]}
    [WARN] Backup key: {tokens[1]} and secondary: {tokens[2]}
    """
    sanitizado = sanitize_log(log_composto)
    for t in tokens:
        assert t not in sanitizado, f"Segredo '{t}' vazou no log sanitizado!"

    assert "sk-****[MASCARADO]****" in sanitizado
    assert "tunnel_****[MASCARADO]****" in sanitizado
    assert "Bearer [TOKEN_MASCARADO]" in sanitizado
    assert "[HASH_MASCARADO]" in sanitizado
