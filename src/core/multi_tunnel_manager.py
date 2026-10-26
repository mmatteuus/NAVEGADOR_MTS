"""Gerenciador de múltiplos túneis simultâneos (OpenAI, Cloudflare, Custom)."""
from __future__ import annotations

import shutil
import threading
from typing import Any, Dict, List, Optional

from .config import current_config, get_tunnel_id
from .tunnel_config import list_tunnel_profiles
from .tunnel_health import get_health_file_path
from .tunnel_service import TunnelService, tunnel_service


def _build_command_for_profile(profile: Dict[str, Any]) -> Optional[List[str]]:
    """Constrói a linha de comando para túneis cloudflared ou customizados."""
    cmd = profile.get("command")
    if isinstance(cmd, list) and cmd:
        return [str(x) for x in cmd]
    if isinstance(cmd, str) and cmd.strip():
        return [cmd.strip()]
    provider = str(profile.get("provider", "openai")).strip().lower()
    if provider == "cloudflared":
        binary = shutil.which("cloudflared") or "cloudflared"
        token = str(profile.get("token", "")).strip()
        if token:
            return [binary, "tunnel", "run", "--token", token]
        target_url = str(profile.get("url") or f"http://127.0.0.1:{current_config.mcp_port}").strip()
        return [binary, "tunnel", "--url", target_url]
    return None


class MultiTunnelManager:
    """Coordena o túnel primário e múltiplos túneis secundários sem colisão de estado."""

    def __init__(self, primary_service: Optional[TunnelService] = None) -> None:
        self._primary: TunnelService = primary_service or tunnel_service
        self._tunnels: Dict[str, TunnelService] = {}
        self._lock = threading.RLock()

    def get_tunnel(self, profile_id: str = "primary") -> Optional[TunnelService]:
        """Retorna a instância TunnelService associada ao profile_id."""
        if not profile_id or profile_id in ("primary", "default"):
            return self._primary
        with self._lock:
            return self._tunnels.get(profile_id)

    def create_or_get_tunnel(
        self, profile_id: str, **overrides: Any
    ) -> TunnelService:
        """Obtém ou instancia um TunnelService isolado para o perfil informado."""
        if not profile_id or profile_id in ("primary", "default"):
            return self._primary
        with self._lock:
            existing = self._tunnels.get(profile_id)
            if existing is not None and not overrides:
                return existing
            stored = next((p for p in list_tunnel_profiles() if p.get("id") == profile_id), {})
            merged = {**stored, **overrides, "id": profile_id}
            provider = str(merged.get("provider", "openai")).strip().lower()
            tid = str(merged.get("tunnel_id", "")).strip() or None
            hfile = merged.get("health_file") or get_health_file_path(profile_id)
            cmd = _build_command_for_profile(merged)
            svc = TunnelService(
                profile_id=profile_id,
                tunnel_id=tid,
                health_file=hfile,
                provider=provider,
                custom_command=cmd,
            )
            self._tunnels[profile_id] = svc
            return svc

    def start_tunnel(self, profile_id: str = "primary", **overrides: Any) -> bool:
        """Inicia um túnel específico (primário ou secundário) sem afetar os demais."""
        svc = self.create_or_get_tunnel(profile_id, **overrides)
        return svc.start()

    def stop_tunnel(self, profile_id: str = "primary") -> bool:
        """Interrompe um túnel específico pelo seu profile_id."""
        svc = self.get_tunnel(profile_id)
        if svc is None:
            return False
        svc.stop()
        return True

    def start_all(self) -> Dict[str, bool]:
        """Inicia o túnel primário (se configurado) e todos os perfis habilitados."""
        results: Dict[str, bool] = {}
        if get_tunnel_id():
            results["primary"] = self._primary.start()
        for prof in list_tunnel_profiles():
            pid = str(prof.get("id", "")).strip()
            if pid and pid not in ("primary", "default") and prof.get("enabled", True):
                results[pid] = self.start_tunnel(pid, **prof)
        return results

    def stop_all(self) -> None:
        """Para o túnel primário e todos os túneis secundários ativos."""
        self._primary.stop()
        with self._lock:
            services = list(self._tunnels.values())
        for svc in services:
            svc.stop()

    def _serialize_service(self, pid: str, svc: TunnelService) -> Dict[str, Any]:
        return {
            "id": pid,
            "provider": getattr(svc, "provider", "openai"),
            "isActive": svc.is_active,
            "isReady": svc.is_ready,
            "lastError": svc.last_error,
            "healthFile": str(svc.health_file_path),
        }

    def get_status(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Consulta o status de um túnel específico ou o mapa consolidado de todos os túneis."""
        if profile_id is not None:
            svc = self.get_tunnel(profile_id)
            if svc is None:
                return {"id": profile_id, "isActive": False, "isReady": False, "lastError": "Não encontrado"}
            return self._serialize_service(profile_id, svc)
        tunnels = {"primary": self._serialize_service("primary", self._primary)}
        with self._lock:
            for pid, svc in self._tunnels.items():
                tunnels[pid] = self._serialize_service(pid, svc)
        return {"primary": tunnels["primary"], "tunnels": tunnels, "profiles": list_tunnel_profiles()}

    def list_statuses(self) -> List[Dict[str, Any]]:
        """Retorna lista de status de todos os serviços de túnel gerenciados."""
        return list(self.get_status()["tunnels"].values())


multi_tunnel_manager = MultiTunnelManager()

__all__ = ["MultiTunnelManager", "multi_tunnel_manager"]
