"""Formatador de respostas e envelopes para o Model Context Protocol (MCP).

Padroniza payloads de sucesso e erro segundo a especificação JSON-RPC do MCP,
suportando texto puro, dados JSON estruturados e imagens em Base64.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


def format_mcp_result(result_data: Any) -> Dict[str, Any]:
    """Converte resultados arbitrários em conteúdo estruturado compatível com o MCP."""
    content: List[Dict[str, Any]] = []
    if isinstance(result_data, dict) and any(
        k in result_data for k in ("base64", "screenshot", "imageBase64")
    ):
        b64_img = (
            result_data.get("base64")
            or result_data.get("screenshot")
            or result_data.get("imageBase64")
        )
        mime = result_data.get("mimeType") or (
            "image/jpeg" if result_data.get("format") in ("jpeg", "jpg") else "image/png"
        )
        content.append({"type": "image", "data": str(b64_img), "mimeType": mime})
        info = {
            k: v
            for k, v in result_data.items()
            if k not in ("base64", "screenshot", "imageBase64")
        }
        if info:
            content.append({
                "type": "text",
                "text": json.dumps(info, ensure_ascii=False, indent=2)
            })
    else:
        text_repr = (
            result_data
            if isinstance(result_data, str)
            else json.dumps(result_data, ensure_ascii=False, indent=2)
        )
        content.append({"type": "text", "text": text_repr})

    return {"content": content, "isError": False}


def format_mcp_error(message: str) -> Dict[str, Any]:
    """Gera envelope de erro padronizado para o protocolo MCP."""
    return {"content": [{"type": "text", "text": str(message)}], "isError": True}


__all__ = ["format_mcp_result", "format_mcp_error"]
