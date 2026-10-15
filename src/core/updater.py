"""Módulo de Verificação e Download de Atualizações do BROWSER MTS.

Responsabilidades:
- Consulta resiliente ao repositório GitHub (commits e releases) para detectar novidades.
- Atualização leve por substituição de arquivos (ZIP da branch main) sem reinstalar o app.
- Fallback automático para instalador .exe quando o aplicativo ainda não está instalado.
- Comparação semântica de versões sequenciais (ex: 2.1.3 > 2.1.2).
- Download ou cópia com barra de progresso em tempo real.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import time
from typing import Callable, Optional
import urllib.request
import zipfile
from .config import current_config

APP_VERSION: str = "2.1.3"
TARGET_UPDATE_VERSION: str = APP_VERSION

# Repositório oficial que a aplicação consulta para se atualizar
GITHUB_OWNER: str = "mmatteuus"
GITHUB_REPO: str = "NAVEGADOR_MTS"
GITHUB_BRANCH: str = "main"

DEFAULT_RELEASE_URL: str = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_COMMIT_URL: str = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
GITHUB_ZIP_URL: str = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"

# Arquivo marcador gravado após cada atualização por arquivos
VERSION_MARKER: str = ".mts_version"


@dataclass(frozen=True)
class UpdateInfo:
    """Metadados de uma versão disponível para atualização.

    update_type:
        - "files": atualização leve, substitui os arquivos locais pelo conteúdo do GitHub.
        - "installer": instalação/atualização completa via instalador .exe (Inno Setup).
    """
    version: str
    release_notes: str
    download_url: str
    asset_name: str
    is_newer: bool
    update_type: str = "installer"


def parse_version_tuple(v_str: str) -> tuple[int, ...]:
    """Converte strings como 'v2.1.0' ou '2.0.0' em tupla de inteiros comparáveis."""
    clean = str(v_str).strip().lstrip("vV").split("+")[0]
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) if parts else (0, 0, 0)


def bump_version(version: str, part: str = "patch") -> str:
    """Incrementa sequencialmente a versão (2.1.3 -> 2.1.4 para 'patch')."""
    major, minor, patch = (parse_version_tuple(version) + (0, 0, 0))[:3]
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def find_local_installer_path() -> Optional[Path]:
    """Busca o instalador com maior versão em diretórios locais conhecidos."""
    candidates = []
    directories = [
        current_config.project_root / "dist_installer",
        Path(sys.executable).resolve().parent / "dist_installer",
    ]
    for directory in directories:
        if directory.is_dir():
            candidates.extend(directory.glob("NAVEGADOR_MTS_Instalador_v*.exe"))
    valid = [p for p in candidates if p.is_file() and p.stat().st_size > 1_000_000]
    return max(valid, key=lambda p: parse_version_tuple(p.stem.split("_v")[-1]),
               default=None)


def _installer_version(path: Path) -> str:
    """Extrai a versão do nome padronizado do instalador."""
    return path.stem.split("_v")[-1] if "_v" in path.stem else "0.0.0"


def get_local_installer() -> Optional[Path]:
    """Compatibilidade: retorna o instalador local mais recente, se existir."""
    return find_local_installer_path()


def is_app_installed() -> bool:
    """Detecta se o aplicativo está instalado/empacotado e pode ser atualizado por arquivos.

    Um executável congelado (PyInstaller) já está instalado por definição.
    Uma execução a partir do código-fonte só é atualizável se a árvore de arquivos existir.
    """
    if getattr(sys, "frozen", False):
        return True
    return (current_config.project_root / "src").is_dir()


def get_current_commit_hash() -> Optional[str]:
    """Obtém o hash do commit atual: marcador de versão local ou repositório git."""
    try:
        marker = current_config.project_root / VERSION_MARKER
        if marker.is_file():
            stored = marker.read_text(encoding="utf-8").strip()
            if stored:
                return stored[:12]

        head = current_config.project_root / ".git" / "HEAD"
        if head.is_file():
            content = head.read_text(encoding="utf-8").strip()
            if content.startswith("ref:"):
                ref_file = current_config.project_root / ".git" / content[5:].strip()
                if ref_file.is_file():
                    return ref_file.read_text(encoding="utf-8").strip()[:12]
            elif content:
                return content[:12]
    except Exception:
        pass
    return None


def save_current_commit_hash(commit_hash: str) -> None:
    """Grava o marcador local com o commit aplicado para evitar atualizações repetidas."""
    try:
        current_config.project_root.joinpath(VERSION_MARKER).write_text(
            commit_hash.strip(), encoding="utf-8"
        )
    except Exception:
        pass


def _fetch_json(url: str, timeout: float = 6.0) -> Optional[dict]:
    """Executa GET autenticado por User-Agent e devolve o JSON decodificado."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"BROWSER-MTS-Updater/{APP_VERSION}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    return None


def check_for_updates(api_url: str = DEFAULT_RELEASE_URL,
                      allow_local_fallback: bool = True) -> Optional[UpdateInfo]:
    """Verifica atualizações em três níveis, na ordem de preferência.

    1. Commits novos na branch main  -> atualização leve por substituição de arquivos.
    2. Release publicada com .exe    -> atualização/instalação via instalador.
    3. Instalador compilado local    -> último recurso offline.
    """
    # 1. Atualização leve por arquivos (GitHub -> aplicação já instalada)
    if is_app_installed():
        commit_data = _fetch_json(GITHUB_COMMIT_URL)
        if commit_data:
            remote_hash = (commit_data.get("sha") or "")[:12]
            message = (commit_data.get("commit", {}).get("message") or "").strip()
            local_hash = get_current_commit_hash()
            if remote_hash and remote_hash != local_hash:
                return UpdateInfo(
                    version=APP_VERSION,
                    release_notes=message.splitlines()[0][:200] if message
                    else "Novas alterações disponíveis no repositório oficial.",
                    download_url=GITHUB_ZIP_URL,
                    asset_name=f"NAVEGADOR_MTS_{GITHUB_BRANCH}.zip",
                    is_newer=True,
                    update_type="files",
                )

    # 2. Release oficial com instalador .exe (versão sequencial mais nova)
    release_data = _fetch_json(api_url)
    if release_data:
        tag = release_data.get("tag_name", "")
        notes = release_data.get("body") or "Melhorias de desempenho e correções gerais."
        is_newer = parse_version_tuple(tag) > parse_version_tuple(APP_VERSION)
        d_url, a_name = "", ""
        for asset in release_data.get("assets", []):
            if asset.get("name", "").endswith(".exe"):
                d_url = asset.get("browser_download_url", "")
                a_name = asset.get("name", "")
                break
        if is_newer and d_url:
            return UpdateInfo(version=tag, release_notes=notes, download_url=d_url,
                              asset_name=a_name, is_newer=True, update_type="installer")

    # 3. Fallback: instalador compilado localmente
    if allow_local_fallback:
        loc = find_local_installer_path()
        if loc and parse_version_tuple(_installer_version(loc)) > parse_version_tuple(APP_VERSION):
            return UpdateInfo(
                version=_installer_version(loc),
                release_notes="Instalador local mais recente disponível.",
                download_url=str(loc), asset_name=loc.name, is_newer=True,
                update_type="installer",
            )
    return None


def download_and_launch_update(
    update_info: UpdateInfo,
    progress_callback: Optional[Callable[[float], None]] = None,
    on_ready_to_install: Optional[Callable[[], None]] = None,
) -> bool:
    """Executa a atualização adequada ao tipo detectado (arquivos ou instalador)."""
    if not update_info.download_url and update_info.update_type != "files":
        return False
    if update_info.update_type == "files":
        return apply_files_update(update_info, progress_callback, on_ready_to_install)
    return download_and_launch_installer(update_info, progress_callback, on_ready_to_install)


def _download_to(url: str, destination: Path,
                 progress_callback: Optional[Callable[[float], None]] = None,
                 base: float = 0.0, span: float = 1.0, timeout: float = 60.0) -> None:
    """Baixa uma URL para disco reportando progresso proporcional no intervalo [base, base+span]."""
    req = urllib.request.Request(url, headers={"User-Agent": f"BROWSER-MTS-Updater/{APP_VERSION}"})
    staged = Path(str(destination) + ".part")
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(staged, "wb") as out_file:
        total_size = int(resp.headers.get("Content-Length", 0) or 0)
        downloaded, chunk_size = 0, 65536
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if progress_callback and total_size > 0:
                progress_callback(base + span * min(1.0, downloaded / total_size))
    if total_size and downloaded != total_size:
        try:
            staged.unlink(missing_ok=True)
        except OSError:
            pass
        raise IOError("Download incompleto.")
    os.replace(staged, destination)
    if progress_callback:
        progress_callback(base + span)


def download_and_launch_installer(
    update_info: UpdateInfo,
    progress_callback: Optional[Callable[[float], None]] = None,
    on_ready_to_install: Optional[Callable[[], None]] = None,
) -> bool:
    """Baixa (ou copia) o instalador .exe e o executa para instalação in-place."""
    temp_dir = tempfile.gettempdir()
    safe_name = Path(update_info.asset_name
                     or f"NAVEGADOR_MTS_Instalador_v{update_info.version}.exe").name
    target_path = Path(temp_dir) / safe_name
    staged_path = Path(str(target_path) + ".part")
    try:
        if not update_info.download_url.startswith(("http://", "https://")):
            src_path = Path(update_info.download_url)
            if not src_path.exists():
                return False
            for step in (0.3, 0.6, 0.9):
                if progress_callback:
                    progress_callback(step)
                time.sleep(0.02)
            if src_path.resolve() != target_path.resolve():
                shutil.copyfile(src_path, staged_path)
                os.replace(staged_path, target_path)
            if progress_callback:
                progress_callback(1.0)
        else:
            _download_to(update_info.download_url, target_path, progress_callback, 0.0, 1.0, 30.0)

        # Flags Inno Setup: fecha instâncias anteriores e substitui in-place sem travar
        subprocess.Popen([str(target_path), "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS"])
        if on_ready_to_install:
            on_ready_to_install()
        return True
    except Exception:
        try:
            staged_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def apply_files_update(
    update_info: UpdateInfo,
    progress_callback: Optional[Callable[[float], None]] = None,
    on_ready_to_install: Optional[Callable[[], None]] = None,
) -> bool:
    """Atualiza a aplicação instalada substituindo os arquivos locais pelos do GitHub.

    Baixa o ZIP da branch main, extrai em diretório temporário isolado e delega a
    substituição a um script .bat que aguarda o encerramento do processo atual,
    copia os arquivos com robocopy, limpa os temporários e reinicia o aplicativo.
    """
    work_dir = Path(tempfile.gettempdir())
    zip_path = work_dir / (update_info.asset_name or f"NAVEGADOR_MTS_{GITHUB_BRANCH}.zip")
    extract_dir = work_dir / f"NAVEGADOR_MTS_update_{os.getpid()}_{int(time.time())}"
    if progress_callback:
        progress_callback(0.05)
    try:
        # 1. Download do código-fonte oficial
        _download_to(update_info.download_url, zip_path, progress_callback, 0.05, 0.45, 90.0)

        # 2. Extração em diretório temporário isolado
        if progress_callback:
            progress_callback(0.55)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as archive:
            _safe_extract(archive, extract_dir)

        roots = [d for d in extract_dir.iterdir() if d.is_dir()]
        if not roots:
            raise IOError("ZIP extraído sem diretório raiz.")
        source_root = roots[0]
        if not (source_root / "src").is_dir():
            raise IOError("Estrutura inesperada: pasta 'src' ausente no ZIP oficial.")

        # 3. Script de substituição que roda após o encerramento do aplicativo
        if progress_callback:
            progress_callback(0.75)
        commit_hash = get_remote_commit_hash() or ""
        script_path = _create_update_script(source_root, extract_dir, zip_path, commit_hash)
        if progress_callback:
            progress_callback(0.9)

        _spawn_detached(script_path)
        if on_ready_to_install:
            on_ready_to_install()
        if progress_callback:
            progress_callback(1.0)
        return True
    except Exception:
        try:
            zip_path.unlink(missing_ok=True)
            shutil.rmtree(extract_dir, ignore_errors=True)
        except OSError:
            pass
        return False


def get_remote_commit_hash() -> Optional[str]:
    """Consulta o hash do commit mais recente da branch main no GitHub."""
    data = _fetch_json(GITHUB_COMMIT_URL)
    if data:
        return (data.get("sha") or "")[:12] or None
    return None


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extrai o ZIP garantindo que nenhum caminho escape do diretório de destino."""
    dest_root = destination.resolve()
    for member in archive.infolist():
        target = (dest_root / member.filename).resolve()
        if not str(target).startswith(str(dest_root)):
            raise IOError("ZIP contém caminho fora do diretório de destino.")
    archive.extractall(destination)


def _spawn_detached(script_path: Path) -> None:
    """Inicia o script de atualização desacoplado do processo atual."""
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | \
                        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(["cmd.exe", "/c", str(script_path)], creationflags=creationflags,
                     close_fds=True, cwd=str(Path(tempfile.gettempdir())))


def _create_update_script(source_root: Path, extract_dir: Path,
                          zip_path: Path, commit_hash: str) -> Path:
    """Gera o .bat que espera o app fechar, substitui os arquivos e reinicia a aplicação."""
    script_path = Path(tempfile.gettempdir()) / f"NAVEGADOR_MTS_apply_{os.getpid()}.bat"
    project_root = Path(current_config.project_root).resolve()
    pid = os.getpid()

    if getattr(sys, "frozen", False):
        restart_cmd = f'start "" "{sys.executable}"'
    else:
        restart_cmd = f'start "" "{sys.executable}" "{project_root / "entrypoint.py"}"'

    marker_line = ""
    if commit_hash:
        marker_line = f'> "{project_root}\\{VERSION_MARKER}" echo {commit_hash}'

    def win(p: Path) -> str:
        return str(p).replace("/", "\\")

    content = f'''@echo off
chcp 65001 >nul
title NAVEGADOR MTS - Aplicando Atualizacao
echo Aplicando atualizacao do NAVEGADOR MTS...
set "PID={pid}"
set /a TRIES=0

:WAIT_LOOP
tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
if errorlevel 1 goto DO_UPDATE
set /a TRIES+=1
if %TRIES% GEQ 60 goto DO_UPDATE
timeout /t 1 /nobreak >nul
goto WAIT_LOOP

:DO_UPDATE
echo Substituindo arquivos da aplicacao...
robocopy "{win(source_root)}\\src" "{win(project_root)}\\src" /E /R:2 /W:1 /NP /NFL /NDL /NJH /NJS /XD __pycache__
if exist "{win(source_root)}\\entrypoint.py" copy /y "{win(source_root)}\\entrypoint.py" "{win(project_root)}\\entrypoint.py" >nul
if exist "{win(source_root)}\\requirements.txt" copy /y "{win(source_root)}\\requirements.txt" "{win(project_root)}\\requirements.txt" >nul
{marker_line}

echo Limpando arquivos temporarios...
rmdir /s /q "{win(extract_dir)}" 2>nul
del /f /q "{win(zip_path)}" 2>nul

echo Reiniciando NAVEGADOR MTS...
{restart_cmd}
del /f /q "%~f0" 2>nul
exit /b 0
'''
    script_path.write_text(content, encoding="utf-8")
    return script_path
