"""Validação lexical e retenção de ancestrais contra trocas de diretórios."""
from __future__ import annotations

import os
import re
from contextlib import ExitStack, contextmanager
from pathlib import Path
from .folder_handles import LockedHandle

RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", re.I)
INVALID_CHARS = re.compile(r'[\x00-\x1f:<>"|?*]')


def local_absolute(value):
    root = Path(os.path.abspath(value))
    if not root.drive or str(root).startswith("\\\\"):
        raise ValueError("FOLDER_LOCAL_ROOT_REQUIRED")
    return root


def relative_target(root, value):
    if not isinstance(value, str):
        raise ValueError("FOLDER_PATH_INVALID")
    rel = Path(value)
    if rel.is_absolute() or rel.drive or rel.root:
        raise ValueError("FOLDER_ESCAPE_DENIED")
    for part in rel.parts:
        if part == ".." or part.endswith((" ", ".")) or RESERVED.match(part):
            raise ValueError("FOLDER_PATH_INVALID")
        # Validação otimizada via regex de caracteres inválidos (evita loop e generator comprehension)
        if INVALID_CHARS.search(part):
            raise ValueError("FOLDER_PATH_INVALID")
    return root / rel


@contextmanager
def pinned_directories(path):
    """Nega remoção/rename de cada ancestral enquanto um efeito está pendente."""
    with ExitStack() as stack:
        handles = {}
        for directory in [*reversed(path.parents), path]:
            handles[directory] = stack.enter_context(LockedHandle(directory, directory=True))
        yield handles


def root_identity(root):
    with pinned_directories(root) as handles:
        return handles[root].identity()
