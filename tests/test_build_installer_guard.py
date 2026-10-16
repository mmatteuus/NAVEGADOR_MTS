"""Regressão do guard que lê a versão real do CArchive PyInstaller."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from build_installer import validate_packaged_executable


class _FakeArchive:
    """Fornece a API mínima do CArchiveReader sem executar um EXE."""

    def __init__(self, path):
        self.path = path

    def open_embedded_archive(self, name):
        assert name == "PYZ.pyz"
        return self

    def extract(self, name):
        assert name == "src.version"
        return SimpleNamespace(co_consts=("docstring", "9.9.9"))


def test_guard_rejects_stale_embedded_version(tmp_path):
    """Uma versão antiga embutida falha mesmo que o arquivo contenha 2.1.3."""
    executable = tmp_path / "NAVEGADOR_MTS.exe"
    executable.write_bytes(b"2.1.3")
    with patch("build_installer.CArchiveReader", _FakeArchive), pytest.raises(RuntimeError):
        validate_packaged_executable(str(executable))
