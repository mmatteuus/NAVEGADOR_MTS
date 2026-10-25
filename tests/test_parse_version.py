"""Suíte de Testes Automatizados para parse_version_tuple.

Valida a conversão e sanitização de versões em tuplas numéricas para comparação semântica.
"""

from src.core.update_network import parse_version_tuple


def test_parse_version_tuple_standard():
    """Valida formatos padrões de versão numéricos."""
    assert parse_version_tuple("1.0.0") == (1, 0, 0)
    assert parse_version_tuple("2.15.3") == (2, 15, 3)
    assert parse_version_tuple("0.0.1") == (0, 0, 1)


def test_parse_version_tuple_prefixes_and_whitespace():
    """Valida prefixos 'v'/'V' e remoção de espaços em branco."""
    assert parse_version_tuple("v1.2.3") == (1, 2, 3)
    assert parse_version_tuple("V2.0.0") == (2, 0, 0)
    assert parse_version_tuple("  v3.4.5  ") == (3, 4, 5)


def test_parse_version_tuple_build_metadata_and_suffixes():
    """Valida tratamento de metadados de build com '+' e sufixos não numéricos."""
    assert parse_version_tuple("1.0.0+20230101") == (1, 0, 0)
    assert parse_version_tuple("2.1.0-beta.1") == (2, 1)
    assert parse_version_tuple("v1.2.3+build.104") == (1, 2, 3)


def test_parse_version_tuple_multi_components():
    """Valida versões com mais de 3 partes numéricas."""
    assert parse_version_tuple("1.2.3.4") == (1, 2, 3, 4)
    assert parse_version_tuple("2.0.0.1.5") == (2, 0, 0, 1, 5)


def test_parse_version_tuple_invalid_and_fallbacks():
    """Valida fallback para (0, 0, 0) em entradas inválidas ou vazias."""
    assert parse_version_tuple("invalid") == (0, 0, 0)
    assert parse_version_tuple("") == (0, 0, 0)
    assert parse_version_tuple("v") == (0, 0, 0)
    assert parse_version_tuple("  ") == (0, 0, 0)
    assert parse_version_tuple(None) == (0, 0, 0)
