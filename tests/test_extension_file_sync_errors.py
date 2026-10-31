from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.core.extension_file_sync import sync_extension_files


def test_sync_extension_files_oserror_during_copy(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """
    Testa o caminho de erro OSError durante a cópia de arquivos individuais.
    O diretório ainda deve ser adicionado à lista 'synced', apesar da falha na cópia.
    """
    caplog.set_level(logging.DEBUG, logger="BrowserMTS.ExtensionSync")

    src_dir = tmp_path / "src_extension"
    src_dir.mkdir()
    (src_dir / "manifest.json").write_text("{}")

    target_dir = tmp_path / "target_extension"

    with patch("src.core.extension_file_sync.get_source_extension_dir", return_value=src_dir), \
         patch("src.core.extension_file_sync.get_known_extension_targets", return_value=[target_dir]), \
         patch("src.core.extension_file_sync.shutil.copy2", side_effect=OSError("Erro de disco mockado")):

        synced = sync_extension_files()

        assert target_dir in synced
        assert "Falha ao copiar" in caplog.text
        assert "Erro de disco mockado" in caplog.text


def test_sync_extension_files_generic_exception_during_sync(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """
    Testa o caminho de exceção genérica ao processar um diretório alvo.
    O diretório não deve ser adicionado à lista 'synced'.
    """
    caplog.set_level(logging.DEBUG, logger="BrowserMTS.ExtensionSync")

    src_dir = tmp_path / "src_extension"
    src_dir.mkdir()
    (src_dir / "manifest.json").write_text("{}")

    target_dir = tmp_path / "target_extension"

    # Criar parent dir real no tmp_path porque a logica faz: if not target.parent.exists(): continue
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    with patch("src.core.extension_file_sync.get_source_extension_dir", return_value=src_dir), \
         patch("src.core.extension_file_sync.get_known_extension_targets", return_value=[target_dir]), \
         patch("src.core.extension_file_sync.Path.mkdir", side_effect=Exception("Permissão negada mockada")):

        synced = sync_extension_files()

        assert target_dir not in synced
        assert "Erro ao sincronizar diretório de extensão" in caplog.text
        assert "Permissão negada mockada" in caplog.text
