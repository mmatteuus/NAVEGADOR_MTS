"""Utilitários de Configuração Multi-IA e Perfis Multi-Túnel para o NAVEGADOR MTS.

Gera e instala configurações MCP isoladas por agente (Claude, Google Gemini,
OpenCode, Cursor, OpenAI Codex e ChatGPT) e gerencia perfis extras de túneis.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import current_config, get_tunnel_id, get_tunnel_name, save_tunnel_id, save_tunnel_name
from ..core.tunnel_config import _read_tunnel_data, _write_tunnel_data

AI_PROVIDERS: Dict[str, Dict[str, str]] = {
    "claude": {"label": "Claude Desktop / Code", "agent_id": "claude-agent"},
    "gemini": {"label": "Google Gemini / Antigravity", "agent_id": "gemini-agent"},
    "opencode": {"label": "OpenCode CLI / Desktop", "agent_id": "opencode-agent"},
    "cursor": {"label": "Cursor IDE", "agent_id": "cursor-agent"},
    "codex": {"label": "OpenAI Codex CLI", "agent_id": "codex-agent"},
    "chatgpt": {"label": "ChatGPT (Túnel HTTP)", "agent_id": "chatgpt-tunnel"},
}


def get_stdio_command() -> Tuple[str, List[str]]:
    """Retorna o executável e argumentos para iniciar o NAVEGADOR MTS em modo MCP Stdio."""
    if getattr(sys, "frozen", False):
        exe = str(Path(sys.executable).parent / "mcp_stdio" / "NAVEGADOR_MTS_MCP.exe")
        return exe, []
    exe = sys.executable
    entrypoint = str(Path(__file__).resolve().parents[2] / "entrypoint.py")
    return exe, [entrypoint, "--stdio"]


def generate_ai_mcp_config(provider: str) -> str:
    """Gera o bloco JSON de configuração MCP para o provedor de IA informado."""
    key = (provider or "claude").strip().lower()
    meta = AI_PROVIDERS.get(key, {"label": key.title(), "agent_id": f"{key}-agent"})
    cmd, args = get_stdio_command()
    env = {"BROWSER_MTS_AGENT_ID": meta["agent_id"]}
    server_entry: Dict[str, Any] = {"command": cmd, "args": args, "env": env}

    if key == "chatgpt":
        payload: Dict[str, Any] = {
            "provider": "chatgpt",
            "mcpServerUrl": f"http://127.0.0.1:{current_config.mcp_port}/mcp",
            "tunnelId": get_tunnel_id() or "Configure seu tunnel_id na aba Configurações",
            "mcpServers": {"navegador-mts": server_entry},
        }
    elif key == "opencode":
        payload = {
            "mcp": {"navegador-mts": {"type": "local", "command": [cmd, *args], "environment": env}},
            "mcpServers": {"navegador-mts": server_entry},
        }
    else:
        payload = {"mcpServers": {"navegador-mts": server_entry}}

    return json.dumps(payload, indent=2, ensure_ascii=False)


def get_default_ai_config_path(provider: str) -> Path:
    """Retorna o caminho de configuração padrão do cliente de IA no Windows."""
    key = provider.strip().lower()
    appdata = Path(os.environ.get("APPDATA", str(Path.home())))
    home = Path.home()
    paths = {
        "claude": appdata / "Claude" / "claude_desktop_config.json",
        "gemini": home / ".gemini" / "antigravity" / "mcp_config.json",
        "opencode": home / ".config" / "opencode" / "opencode.json",
        "cursor": home / ".cursor" / "mcp.json",
        "codex": home / ".codex" / "mcp.json",
    }
    return paths.get(key, current_config.app_data_dir / f"mcp_{key}.json")


def install_ai_config_auto(provider: str, target_path: Optional[Path] = None) -> Tuple[bool, str]:
    """Mescla de forma não-destrutiva a configuração do NAVEGADOR MTS no cliente de IA."""
    key = provider.strip().lower()
    if key == "chatgpt":
        tid = get_tunnel_id()
        return True, f"Túnel ChatGPT: {tid or 'Defina o ID tunnel_... em Configurações'}"
    dest = target_path or get_default_ai_config_path(key)
    try:
        existing: Dict[str, Any] = {}
        if dest.exists():
            existing = json.loads(dest.read_text(encoding="utf-8"))
        new_cfg = json.loads(generate_ai_mcp_config(key))
        existing.setdefault("mcpServers", {})["navegador-mts"] = new_cfg["mcpServers"]["navegador-mts"]
        if key == "opencode" and "mcp" in new_cfg:
            existing.setdefault("mcp", {})["navegador-mts"] = new_cfg["mcp"]["navegador-mts"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return True, f"Configurado em {dest.name}"
    except Exception as exc:
        return False, f"Snippet copiado ({exc})"


def list_tunnel_profiles() -> List[Dict[str, str]]:
    """Lista os perfis de túneis salvos (OpenAI, Cloudflare cloudflared ou Custom)."""
    data = _read_tunnel_data()
    profiles = data.get("profiles", [])
    if not isinstance(profiles, list):
        profiles = []
    cur_id, cur_name = get_tunnel_id(), get_tunnel_name() or "Principal"
    if cur_id and not any(p.get("tunnel_id") == cur_id for p in profiles if isinstance(p, dict)):
        profiles.insert(0, {"name": cur_name, "tunnel_id": cur_id, "provider": "openai"})
    return [p for p in profiles if isinstance(p, dict)]


def save_tunnel_profile(name: str, tunnel_id: str, provider: str = "openai") -> List[Dict[str, str]]:
    """Salva ou atualiza um perfil de túnel na configuração local e o torna ativo se válido."""
    clean_name = (name or "Túnel Extra").strip()[:60]
    clean_id = (tunnel_id or "").strip()
    prov = (provider or "openai").strip().lower()
    if prov == "openai" and clean_id and not re.fullmatch(r"tunnel_[0-9a-f]{32}", clean_id):
        raise ValueError("Para OpenAI, o ID deve ter prefixo tunnel_ e 32 dígitos hexadecimais.")
    data = _read_tunnel_data()
    profiles = [p for p in data.get("profiles", []) if isinstance(p, dict) and p.get("name") != clean_name]
    profiles.append({"name": clean_name, "tunnel_id": clean_id, "provider": prov})
    data["profiles"] = profiles
    _write_tunnel_data(data)
    if prov == "openai" and re.fullmatch(r"tunnel_[0-9a-f]{32}", clean_id):
        save_tunnel_id(clean_id)
        save_tunnel_name(clean_name)
    return profiles
