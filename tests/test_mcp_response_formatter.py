"""Suíte de testes para o formatador de respostas e envelopes do MCP.

Testa as funções format_mcp_result e format_mcp_error cobrindo:
1. Resultados de texto simples (strings).
2. Estruturas JSON arbritárias (dicionários e listas sem imagem).
3. Payload com imagem em Base64 usando chaves base64, screenshot e imageBase64.
4. Dedução automática de mimeType (jpeg/jpg x png padrão).
5. Separação de metadados extras e formatação format_mcp_error.
"""

from __future__ import annotations

import json
from src.mcp.response_formatter import format_mcp_error, format_mcp_result


def test_format_mcp_result_string() -> None:
    """Garante que strings puras são formatadas como conteúdo do tipo texto."""
    res = format_mcp_result("Sucesso na operação")
    assert res == {
        "content": [{"type": "text", "text": "Sucesso na operação"}],
        "isError": False,
    }


def test_format_mcp_result_json_structure() -> None:
    """Garante que objetos/dicionários genéricos são serializados em JSON formatado."""
    dados = {"status": "ok", "contador": 42, "itens": ["a", "b"]}
    res = format_mcp_result(dados)
    assert res["isError"] is False
    assert len(res["content"]) == 1
    assert res["content"][0]["type"] == "text"
    parsed = json.loads(res["content"][0]["text"])
    assert parsed == dados


def test_format_mcp_result_base64_image_variants() -> None:
    """Testa detecção de imagem Base64 com chaves 'base64', 'screenshot' e 'imageBase64'."""
    # Variante 1: chave base64 e formato jpeg (mime = image/jpeg)
    p1 = {"base64": "abc123456", "format": "jpeg"}
    r1 = format_mcp_result(p1)
    assert r1["isError"] is False
    assert r1["content"][0] == {
        "type": "image",
        "data": "abc123456",
        "mimeType": "image/jpeg",
    }

    # Variante 2: chave screenshot e formato jpg
    p2 = {"screenshot": "def789", "format": "jpg"}
    r2 = format_mcp_result(p2)
    assert r2["content"][0] == {
        "type": "image",
        "data": "def789",
        "mimeType": "image/jpeg",
    }

    # Variante 3: chave imageBase64 sem formato (mimeType padrão image/png)
    p3 = {"imageBase64": "ghi012"}
    r3 = format_mcp_result(p3)
    assert r3["content"][0] == {
        "type": "image",
        "data": "ghi012",
        "mimeType": "image/png",
    }


def test_format_mcp_result_image_with_mime_override_and_extra_info() -> None:
    """Valida prioridade do mimeType explícito e inclusão de metadados extras."""
    payload = {
        "base64": "xyz890",
        "mimeType": "image/webp",
        "width": 800,
        "height": 600,
    }
    res = format_mcp_result(payload)
    assert res["isError"] is False
    assert len(res["content"]) == 2
    assert res["content"][0] == {
        "type": "image",
        "data": "xyz890",
        "mimeType": "image/webp",
    }
    assert res["content"][1]["type"] == "text"
    extra_info = json.loads(res["content"][1]["text"])
    assert extra_info == {"mimeType": "image/webp", "width": 800, "height": 600}


def test_format_mcp_error() -> None:
    """Garante que a função de erro gera um envelope MCP com isError=True."""
    res = format_mcp_error("Falha ao processar solicitação")
    assert res == {
        "content": [{"type": "text", "text": "Falha ao processar solicitação"}],
        "isError": True,
    }
