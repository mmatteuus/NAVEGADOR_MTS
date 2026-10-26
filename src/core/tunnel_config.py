"""Módulo de Persistência e Identificação de Túneis (Principal e Multi-Túnel)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

SUPPORTED_TUNNEL_PROVIDERS = ("openai", "cloudflared", "custom")


def _get_tunnel_file() -> Path:
    from . import config
    try:
        base = Path(config.current_config.app_data_dir)
    except Exception:
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "browser-mcp-mts"
    return base / "tunnel.json"


def _read_tunnel_data() -> Dict[str, Any]:
    file = _get_tunnel_file()
    try:
        if file.exists():
            return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {}


def _write_tunnel_data(data: Dict[str, Any]) -> None:
    file = _get_tunnel_file()
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, file)


def get_tunnel_id() -> str:
    """Lê o ID efetivo do túnel com override por ambiente e persistência local."""
    from . import config
    candidate = os.environ.get("BROWSER_MTS_TUNNEL_ID", "").strip()
    if not candidate:
        data = _read_tunnel_data()
        candidate = str(data.get("tunnel_id", "")).strip()
        if not candidate:
            try:
                candidate = getattr(config.current_config, "tunnel_id", "").strip()
            except Exception:
                candidate = ""
    return candidate if re.fullmatch(r"tunnel_[0-9a-f]{32}", candidate) else ""


def save_tunnel_id(value: str) -> None:
    """Valida e grava o identificador do túnel atomicamente."""
    identifier = value.strip()
    if not re.fullmatch(r"tunnel_[0-9a-f]{32}", identifier):
        raise ValueError("ID do túnel deve ter prefixo tunnel_ e 32 dígitos hexadecimais.")
    data = _read_tunnel_data()
    data["tunnel_id"] = identifier
    _write_tunnel_data(data)


def get_tunnel_name() -> str:
    """Lê o nome amigável do agente/túnel para identificação facilitada."""
    env_name = os.environ.get("BROWSER_MTS_TUNNEL_NAME", "").strip()
    return env_name or str(_read_tunnel_data().get("tunnel_name", "")).strip()


def save_tunnel_name(name: str) -> str:
    """Salva o nome amigável do agente/túnel atomicamente."""
    clean_name = str(name or "").strip()[:80]
    data = _read_tunnel_data()
    data["tunnel_name"] = clean_name
    _write_tunnel_data(data)
    return clean_name


def get_tunnel_display_label() -> str:
    """Retorna etiqueta descritiva do agente para exibição na UI."""
    name, tid = get_tunnel_name(), get_tunnel_id()
    if name and tid:
        return f"{name} ({tid[:11]}...{tid[-4:]})"
    return name or (f"{tid[:11]}...{tid[-4:]}" if tid else "Não configurado")


def list_tunnel_profiles() -> List[Dict[str, Any]]:
    """Lista todos os perfis de túneis configurados (OpenAI, Cloudflare, Custom)."""
    raw_list = _read_tunnel_data().get("profiles", [])
    return [dict(item) for item in raw_list if isinstance(item, dict)] if isinstance(raw_list, list) else []


def save_tunnel_profile(profile: Optional[Dict[str, Any] | str] = None, **kwargs: Any) -> Dict[str, Any]:
    """Cria ou atualiza um perfil de túnel suportando provedores openai, cloudflared e custom."""
    raw: Dict[str, Any] = dict(profile) if isinstance(profile, dict) else ({"id": profile} if isinstance(profile, str) else {})
    raw.update(kwargs)
    provider = str(raw.get("provider", "openai")).strip().lower()
    if provider not in SUPPORTED_TUNNEL_PROVIDERS:
        raise ValueError(f"Provedor de túnel não suportado: '{provider}'")
    tid = str(raw.get("tunnel_id", "")).strip()
    if provider == "openai" and tid and not re.fullmatch(r"tunnel_[0-9a-f]{32}", tid):
        raise ValueError("ID do túnel OpenAI inválido.")

    data = _read_tunnel_data()
    profiles = [p for p in data.get("profiles", []) if isinstance(p, dict)] if isinstance(data.get("profiles"), list) else []
    pid = str(raw.get("id") or raw.get("profile_id") or f"{provider}_{len(profiles) + 1}").strip()
    cmd = raw.get("command", [])
    entry: Dict[str, Any] = {
        "id": pid,
        "name": str(raw.get("name") or pid).strip()[:80],
        "provider": provider,
        "tunnel_id": tid,
        "token": str(raw.get("token", "")).strip(),
        "command": [str(x) for x in cmd] if isinstance(cmd, list) else ([str(cmd)] if cmd else []),
        "url": str(raw.get("url", "")).strip(),
        "enabled": bool(raw.get("enabled", True)),
    }
    data["profiles"] = [p for p in profiles if p.get("id") != pid] + [entry]
    _write_tunnel_data(data)
    return entry


def remove_tunnel_profile(profile_id: str) -> bool:
    """Remove um perfil de túnel pelo ID e retorna True se existia."""
    data = _read_tunnel_data()
    profiles = [p for p in data.get("profiles", []) if isinstance(p, dict)] if isinstance(data.get("profiles"), list) else []
    filtered = [p for p in profiles if p.get("id") != profile_id]
    if len(filtered) == len(profiles):
        return False
    data["profiles"] = filtered
    _write_tunnel_data(data)
    return True
