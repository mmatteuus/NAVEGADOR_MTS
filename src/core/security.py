"""Módulo de Segurança e Criptografia do BROWSER MTS.

Responsabilidades:
- Criptografia e descriptografia segura de credenciais usando Windows DPAPI nativa.
- Mascaramento visual de credenciais para exibição em interface gráfica.
- Higienização e sanitização automática de segredos em strings de log.
"""

import base64
import ctypes
from ctypes import wintypes
import re
import sys

# Padrões de expressões regulares para sanitização de logs e textos sensíveis
_REGEX_API_KEY = re.compile(r"sk-[a-zA-Z0-9_\-]{16,}")
_REGEX_TUNNEL_ID = re.compile(r"tunnel_[a-f0-9]{20,}")
_REGEX_BEARER = re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE)
_REGEX_HEX_SECRET = re.compile(r"\b[a-fA-F0-9]{32,64}\b")


class SecurityError(Exception):
    """Exceção levantada para falhas em operações criptográficas ou de segurança."""


class _DATA_BLOB(ctypes.Structure):
    """Estrutura Win32 DATA_BLOB para transporte de dados na DPAPI."""
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def encrypt_dpapi(data: str | bytes, description: str = "BrowserMTS_Secret") -> str:
    """Criptografa dados em repouso usando a DPAPI nativa do usuário do Windows.

    Retorna o payload criptografado codificado em Base64.
    """
    if sys.platform != "win32":
        raise SecurityError("DPAPI só é suportada nativamente no sistema operacional Windows.")
    if not data:
        raise ValueError("Os dados a serem criptografados não podem ser vazios.")

    raw_bytes = data.encode("utf-8") if isinstance(data, str) else data
    blob_in = _DATA_BLOB(len(raw_bytes), ctypes.cast(ctypes.create_string_buffer(raw_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_out = _DATA_BLOB()

    # Chama CryptProtectData da crypt32.dll sem expor chave em memória de processo
    res = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), description, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not res:
        err = ctypes.GetLastError()
        raise SecurityError(f"Falha ao criptografar dados via DPAPI (Erro Win32: {err}).")

    try:
        encrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        return base64.b64encode(encrypted_bytes).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def decrypt_dpapi(ciphertext_b64: str) -> str:
    """Descriptografa um payload Base64 cifrado anteriormente com DPAPI.

    Retorna o texto original decodificado em UTF-8.
    """
    if sys.platform != "win32":
        raise SecurityError("DPAPI só é suportada nativamente no sistema operacional Windows.")
    if not ciphertext_b64 or not isinstance(ciphertext_b64, str):
        raise ValueError("O texto cifrado em Base64 deve ser uma string não vazia.")

    try:
        encrypted_bytes = base64.b64decode(ciphertext_b64.encode("ascii"))
    except Exception as exc:
        raise ValueError(f"Payload Base64 inválido para descriptografia: {exc}") from exc

    blob_in = _DATA_BLOB(len(encrypted_bytes), ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_out = _DATA_BLOB()

    # Chama CryptUnprotectData do Windows para reverter a criptografia DPAPI
    res = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not res:
        err = ctypes.GetLastError()
        raise SecurityError(f"Falha ao descriptografar dados via DPAPI (Erro Win32: {err}).")

    try:
        decrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        return decrypted_bytes.decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def mask_credential(secret: str | None, visible_tail: int = 4) -> str:
    """Mascara uma credencial para exibição segura na interface gráfica.

    Exemplo: 'sk-proj-1234567890abcdef' -> 'sk-••••••••••••cdef'.
    """
    if not secret or not secret.strip():
        return "[NÃO CONFIGURADO]"

    clean = secret.strip()
    if len(clean) <= visible_tail:
        return "•" * len(clean)

    if clean.startswith("sk-"):
        tail = clean[-visible_tail:]
        bullets = "•" * max(6, len(clean) - 3 - visible_tail)
        return f"sk-{bullets}{tail}"

    tail = clean[-visible_tail:]
    bullets = "•" * max(8, len(clean) - visible_tail)
    return f"{bullets}{tail}"


def sanitize_log(text: str) -> str:
    """Substitui tokens sensíveis por máscaras fixas em strings de logs."""
    if not text or not isinstance(text, str):
        return "" if text is None else str(text)

    sanitized = _REGEX_API_KEY.sub("sk-****[MASCARADO]****", text)
    sanitized = _REGEX_TUNNEL_ID.sub("tunnel_****[MASCARADO]****", sanitized)
    sanitized = _REGEX_BEARER.sub(r"\1[TOKEN_MASCARADO]", sanitized)
    return _REGEX_HEX_SECRET.sub("[HASH_MASCARADO]", sanitized)
