"""Validações mínimas para credenciais do Secure MCP Tunnel."""


def is_runtime_credential(value: object) -> bool:
    """Aceita somente uma chave não mascarada com prefixo esperado.

    Não impõe tamanho arbitrário: fixtures e chaves válidas podem variar.
    """
    if not isinstance(value, str):
        return False
    clean = value.strip()
    return bool(clean) and clean.startswith("sk-") and len(clean) > 3 and "•" not in clean
