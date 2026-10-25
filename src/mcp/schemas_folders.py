"""Contrato MCP de arquivos concedidos pela interface humana."""
from __future__ import annotations

FOLDER_TOOL = {
    "name": "computer_folder_action",
    "description": "Arquivos de até 1 MiB em pasta atribuída pelo usuário. Use list_roots para obter rootId, read para obter expectedVersion antes de write. Não representa buffers não salvos do editor.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["list_roots", "list", "read", "mkdir", "create", "write"]},
            "rootId": {"type": "string", "description": "Identificador da concessão retornado por list_roots."},
            "path": {"type": "string", "description": "Caminho relativo dentro da pasta concedida."},
            "content": {"type": "string", "description": "Texto UTF-8 para create ou write."},
            "expectedVersion": {"type": "string", "description": "Versão retornada por read; obrigatória em write."}
        },
        "required": ["operation"]
    }
}


def get_folder_tools():
    """Expõe operações limitadas, sem shell, exclusão ou concessão pelo agente."""
    return [dict(FOLDER_TOOL)]
