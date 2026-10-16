"""Regressões do versionamento determinístico e da identidade de release."""

import pytest

from prepare_release import derive_release_version, metadata, validate_identity


def test_execucoes_consecutivas_produzem_ordem_crescente():
    """Cada execução deve gerar versão maior para o mesmo produto base."""
    primeira = derive_release_version("2.1.3", 417)
    segunda = derive_release_version("2.1.3", 418)
    assert tuple(map(int, segunda.split("."))) > tuple(map(int, primeira.split(".")))


def test_rejeita_componentes_e_run_number_invalidos():
    """O formato do Manifest não pode receber componentes fora do limite."""
    with pytest.raises(ValueError):
        derive_release_version("2.1", 1)
    with pytest.raises(ValueError):
        derive_release_version("2.1.3", 65536)


def test_metadata_prende_tag_asset_e_commit():
    """Metadados devem apontar para o mesmo SHA e asset versionado."""
    sha = "a" * 40
    data = metadata("2.1.3.417", sha)
    assert data["tag"] == "v2.1.3.417"
    assert data["asset"].endswith("v2.1.3.417.exe")
    assert data["checksum_asset"].endswith("v2.1.3.417.sha256")
    with pytest.raises(ValueError):
        metadata("2.1.3.417", "b" * 39)
    validate_identity(data, sha)
    data["tag"] = "v2.1.3.416"
    with pytest.raises(ValueError):
        validate_identity(data, sha)
