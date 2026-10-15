"""Regressões para não persistir marcador ou máscara como Runtime API Key."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.core.security import mask_credential
from src.ui import settings_panel


class _Entry:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def delete(self, *_args) -> None:
        self.value = ""

    def insert(self, _index, value: str) -> None:
        self.value = value


class _Switch:
    def get(self) -> int:
        return 0


class _Feedback:
    def configure(self, **_kwargs) -> None:
        return None


class _Config:
    def __init__(self, path: Path) -> None:
        self.credentials_file = path

    def ensure_directories(self) -> None:
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("value", ["[NÃO CONFIGURADO]", "", "   "])
def test_placeholder_and_empty_key_do_not_encrypt(tmp_path: Path, value: str) -> None:
    """Ausência de alteração preserva a credencial já carregada."""
    panel = settings_panel.SettingsPanel.__new__(settings_panel.SettingsPanel)
    panel.entry_key = _Entry(value)
    panel.entry_tunnel = _Entry("tunnel_" + "0" * 32)
    panel.switch_autostart = _Switch()
    panel.lbl_feedback = _Feedback()
    panel._raw_api_key = "sk-existing"
    config = _Config(tmp_path / "runtime_key.enc")
    with patch.object(settings_panel, "current_config", config), patch.object(
        settings_panel, "encrypt_dpapi"
    ) as encrypt, patch.object(settings_panel, "save_tunnel_id"), patch.object(
        settings_panel, "set_autostart_enabled"
    ):
        panel.save_settings()
    encrypt.assert_not_called()
    assert panel._raw_api_key == "sk-existing"


def test_existing_masked_key_does_not_encrypt(tmp_path: Path) -> None:
    """A máscara exibida para uma chave válida é tratada como sem alteração."""
    panel = settings_panel.SettingsPanel.__new__(settings_panel.SettingsPanel)
    panel.entry_key = _Entry(mask_credential("sk-existing-key"))
    panel.entry_tunnel = _Entry("tunnel_" + "0" * 32)
    panel.switch_autostart = _Switch()
    panel.lbl_feedback = _Feedback()
    panel._raw_api_key = "sk-existing-key"
    with patch.object(settings_panel, "current_config", _Config(tmp_path / "key.enc")), patch.object(
        settings_panel, "encrypt_dpapi"
    ) as encrypt, patch.object(settings_panel, "save_tunnel_id"), patch.object(
        settings_panel, "set_autostart_enabled"
    ):
        panel.save_settings()
    encrypt.assert_not_called()


def test_new_syntactically_valid_key_encrypts_once(tmp_path: Path) -> None:
    """Uma nova chave com prefixo válido é protegida exatamente uma vez."""
    panel = settings_panel.SettingsPanel.__new__(settings_panel.SettingsPanel)
    panel.entry_key = _Entry("sk-new-fixture")
    panel.entry_tunnel = _Entry("tunnel_" + "0" * 32)
    panel.switch_autostart = _Switch()
    panel.lbl_feedback = _Feedback()
    panel._raw_api_key = None
    with patch.object(settings_panel, "current_config", _Config(tmp_path / "key.enc")), patch.object(
        settings_panel, "encrypt_dpapi", return_value="ciphertext"
    ) as encrypt, patch.object(settings_panel, "save_tunnel_id"), patch.object(
        settings_panel, "set_autostart_enabled"
    ):
        panel.save_settings()
    encrypt.assert_called_once_with("sk-new-fixture")
    assert (tmp_path / "key.enc").read_text(encoding="utf-8") == "ciphertext"


def test_invalid_environment_key_is_rejected(monkeypatch, tmp_path: Path) -> None:
    """O runtime não envia placeholder ou texto sem prefixo ao túnel."""
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "[NÃO CONFIGURADO]")
    fake_config = SimpleNamespace(credentials_file=tmp_path / "missing.enc")
    with patch("src.core.tunnel_service.current_config", fake_config):
        from src.core.tunnel_service import get_runtime_api_key

        assert get_runtime_api_key() is None
