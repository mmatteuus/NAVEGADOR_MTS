"""Regressão da sintaxe de fechamento controlado do Inno Setup."""

from pathlib import Path


def test_close_applications_filter_uses_inno_comma_separator():
    """O filtro precisa usar vírgulas para o Restart Manager localizar processos."""
    text = Path("installer.iss").read_text(encoding="utf-8")
    line = next(item for item in text.splitlines() if item.startswith("CloseApplicationsFilter="))
    assert "," in line
    assert ";" not in line
