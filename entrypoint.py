"""Ponto de entrada independente para execução e empacotamento do BROWSER MTS.

Este arquivo permite executar o aplicativo ou compilar um executável nativo
Windows sem depender da estrutura do repositório de desenvolvimento.
"""

import os
import sys

# Garante que o diretório raiz esteja no path de importação
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from src.app import main

if __name__ == "__main__":
    main()

