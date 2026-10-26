"""Módulo de Persistência e Identificação do Túnel do Agente."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Dict, Any


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
    if env_name:
        return env_name
    return str(_read_tunnel_data().get("tunnel_name", "")).strip()


def save_tunnel_name(name: str) -> str:
    """Salva o nome amigável do agente/túnel atomicamente."""
    clean_name = str(name or "").strip()[:80]
    data = _read_tunnel_data()
    data["tunnel_name"] = clean_name
    _write_tunnel_data(data)
    return clean_name


def get_tunnel_display_label() -> str:
    """Retorna etiqueta descritiva do agente para exibição na UI."""
    name = get_tunnel_name()
    tid = get_tunnel_id()
    if name and tid:
        short = f"{tid[:11]}...{tid[-4:]}"
        return f"{name} ({short})"
    if name:
        return name
    if tid:
        return f"{tid[:11]}...{tid[-4:]}"
    return "Não configurado"
