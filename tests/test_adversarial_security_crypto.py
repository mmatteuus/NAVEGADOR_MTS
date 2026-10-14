"""Testes Adversariais de Criptografia DPAPI, Mascaramento e Sanitização de Logs.

Validações rigorosas de segurança da informação:
- Integridade da DPAPI com Unicode, emojis, payloads grandes e dados corrompidos.
- Mascaramento visual em UI contra vazamento de caracteres em qualquer tamanho.
- Sanitização regex contra padrões de chaves sk-*, tunnel IDs, Bearer e hashes hex.
"""

from __future__ import annotations
import base64
import pytest
from src.core.security import (
    encrypt_dpapi, decrypt_dpapi, mask_credential, sanitize_log, SecurityError
)


def test_adversarial_dpapi_unicode_and_large_payloads():
    """Garante fidelidade de dados da DPAPI com Unicode, acentos e payloads grandes."""
    segredo_complexo = "Chave-Segura: 🔐 sk-proj-áéíóú-çãõ-1234567890-§©®"
    cifrado = encrypt_dpapi(segredo_complexo)
    assert decrypt_dpapi(cifrado) == segredo_complexo

    payload_grande = "A" * 32768 + "sk-fim-de-payload"
    cifrado_grande = encrypt_dpapi(payload_grande)
    assert decrypt_dpapi(cifrado_grande) == payload_grande


def test_adversarial_dpapi_corrupted_and_tampered_payloads():
    """Valida rejeição segura de payloads corrompidos ou adulterados."""
    with pytest.raises(ValueError):
        encrypt_dpapi("")
    with pytest.raises(ValueError):
        decrypt_dpapi("")
    with pytest.raises(ValueError):
        decrypt_dpapi("not-a-valid-base64-string!!@@")

    # Payload Base64 sintaticamente válido mas com bytes DPAPI adulterados na carga útil
    cifrado = encrypt_dpapi("segredo-valido-12345")
    raw = bytearray(base64.b64decode(cifrado))
    raw[-10] ^= 0xFF  # Adulteração de bits no ciphertext/HMAC
    adulterado_b64 = base64.b64encode(raw).decode("ascii")

    with pytest.raises(SecurityError):
        decrypt_dpapi(adulterado_b64)


def test_adversarial_mask_credential_boundaries():
    """Testa o mascaramento para UI em múltiplos comprimentos e formatos."""
    assert mask_credential(None) == "[NÃO CONFIGURADO]"
    assert mask_credential("") == "[NÃO CONFIGURADO]"
    # Tratamento consistente com whitespace: strip() vazio retorna [NÃO CONFIGURADO]
    assert mask_credential("   ") == "[NÃO CONFIGURADO]"
    assert mask_credential("x") == "•"
    assert mask_credential("1234") == "••••"

    sk_key = "sk-proj-super-secreta-1234567890-final"
    mascarado_sk = mask_credential(sk_key, visible_tail=5)
    assert mascarado_sk.startswith("sk-")
    assert mascarado_sk.endswith("final")
    # Nenhum caractere do miolo deve vazar
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
