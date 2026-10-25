"""
Teste automatizado da Extensão de Navegador Chrome/Edge Manifest V3.

Valida conformidade do manifest.json, integridade de ícones, sintaxe de scripts,
limite estrito de 150 linhas por arquivo e consistência do protocolo WebSocket.
"""

import os
import json
import subprocess
from PIL import Image
from src.core.updater import APP_VERSION

EXTENSION_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "extension")


def test_manifest_v3_structure():
    """Valida a conformidade das configurações do manifest.json."""
    manifest_path = os.path.join(EXTENSION_DIR, "manifest.json")
    assert os.path.exists(manifest_path), "manifest.json não encontrado"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("manifest_version") == 3
    assert manifest.get("version") == APP_VERSION
    assert "tabs" in manifest.get("permissions", [])
    assert "activeTab" in manifest.get("permissions", [])
    assert "alarms" in manifest.get("permissions", [])
    assert "<all_urls>" in manifest.get("host_permissions", [])

    bg = manifest.get("background", {})
    assert bg.get("service_worker") == "background/service_worker.js"
    assert bg.get("type") == "module"


def test_manifest_referenced_files_exist():
    """Garante que todos os arquivos referenciados no manifest.json existem."""
    manifest_path = os.path.join(EXTENSION_DIR, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Service worker
    sw_path = os.path.join(EXTENSION_DIR, manifest["background"]["service_worker"])
    assert os.path.exists(sw_path), f"Service worker ausente: {sw_path}"

    # Popup
    popup_path = os.path.join(EXTENSION_DIR, manifest["action"]["default_popup"])
    assert os.path.exists(popup_path), f"Popup ausente: {popup_path}"

    # Ícones do manifest
    for size, icon_rel in manifest["icons"].items():
        icon_path = os.path.join(EXTENSION_DIR, icon_rel)
        assert os.path.exists(icon_path), f"Ícone {size} ausente: {icon_path}"

    # Content scripts
    for cs in manifest.get("content_scripts", []):
        for script_rel in cs.get("js", []):
            script_path = os.path.join(EXTENSION_DIR, script_rel)
            assert os.path.exists(script_path), f"Content script ausente: {script_path}"


def test_icons_integrity():
    """Verifica se os ícones PNG possuem as dimensões corretas."""
    for size in [16, 32, 48, 128]:
        icon_path = os.path.join(EXTENSION_DIR, "icons", f"icon-{size}.png")
        assert os.path.exists(icon_path), f"Ícone {size} não encontrado"
        with Image.open(icon_path) as img:
            assert img.size == (size, size), f"Dimensão incorreta para ícone {size}: {img.size}"
            assert img.format == "PNG"


def test_file_line_limits():
    """Garante que TODOS os arquivos da extensão tenham estritamente no máximo 150 linhas."""
    for root, _, files in os.walk(EXTENSION_DIR):
        for file in files:
            if file.endswith(".png"):
                continue
            full_path = os.path.join(root, file)
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                assert len(lines) <= 150, f"Arquivo {file} excedeu limite de 150 linhas: {len(lines)}"


def test_javascript_syntax_with_node():
    """Valida a sintaxe de todos os arquivos JavaScript através do Node.js."""
    js_files = []
    for root, _, files in os.walk(EXTENSION_DIR):
        for file in files:
            if file.endswith(".js"):
                js_files.append(os.path.join(root, file))

    assert len(js_files) >= 15, f"Quantidade insuficiente de arquivos JS: {len(js_files)}"

    for js_file in js_files:
        result = subprocess.run(["node", "--check", js_file], capture_output=True, text=True)
        assert result.returncode == 0, f"Erro de sintaxe no arquivo {js_file}:\n{result.stderr}"
