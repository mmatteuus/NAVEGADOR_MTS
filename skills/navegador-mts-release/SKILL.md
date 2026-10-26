---
name: navegador-mts-release
description: Protocolo de engenharia, arquitetura modular (<=150 LOC), testes automatizados (pytest + Node), versionamento SemVer sincronizado e compilação do instalador PyInstaller + Inno Setup do NAVEGADOR MTS. Use sempre que modificar código ou gerar nova versão do NAVEGADOR MTS.
---

# Skill: Engenharia, Manutenção e Release do `NAVEGADOR_MTS`

Use esta skill obrigatoriamente sempre que for **alterar código, corrigir bugs, criar ferramentas MCP, ajustar a interface CustomTkinter/temas ou gerar uma nova versão e instalador** no repositório `D:\MATEUS\Documentos\GitHub\NAVEGADOR_MTS`.

---

## 1. Leitura Prévia Obrigatória no Cérebro Obsidian

1. `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\00-INICIO-AQUI.md`
2. `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\02-PROTOCOLO-PARA-AGENTES.md`
3. `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\03-ARQUITETURA-E-MODULOS.md`
4. `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\09-VERSIONAMENTO-BUILD-E-AUTO-UPDATE.md`

---

## 2. Invariantes Inegociáveis de Código e Segurança

1. **Limite Estrito de $\le 150$ Linhas por Arquivo (LOC)**:
   - Nenhum arquivo `.py` em `src/` ou `tests/` e nenhum arquivo `.js`/`.css`/`.html` em `src/extension/` pode ultrapassar **150 linhas**.
   - Se um arquivo crescer além de 150 linhas, divida-o imediatamente em sub-módulos coesos.
2. **Invariante `SafetyGate` Fail-Closed (Default-Deny)**:
   - Toda ferramenta `computer_*` (exceto `computer_get_status`) exige `safety_gate.is_authorized() == True` e `is_kill_switch_triggered() == False`.
3. **Defesa Anti-Forja de Sessão e Isolamento de Recursos**:
   - Mantenha a validação de `trusted_sid` em `src/mcp/router.py` e os locks por recurso (`tab:<id>`, `hwnd:<id>`, `physical_input`) no `ExecutionCoordinator`.
4. **Compatibilidade Universal Windows (Windows 10, 11 e Server)**:
   - Nunca introduza chamadas Win32/DWM exclusivas do Windows 11 sem bloco `try/except` com fallback gracioso para Windows 10.
   - Na UI (`src/ui/`), use sempre a `FluentPalette` dual-mode (suportando Tema Claro `light`, Tema Escuro `dark` e `system` com contraste WCAG AAA).
5. **Sentinela de Produção (`PROD_PIDS`) e Portas Dinâmicas**:
   - Nos testes, use sempre a fixture `dynamic_port` (nunca use as portas `3456`, `3457` ou `9009`).
   - Nunca mate processos `python.exe` ou `tunnel-client.exe` globalmente.

---

## 3. Passo a Passo Obrigatório para Lançar Nova Versão a Cada Melhoria

Toda melhoria ou correção realizada no `NAVEGADOR_MTS` deve terminar com o ciclo completo de validação, versionamento e compilação do instalador:

### Passo 1: Auditar o Limite de 150 LOC
```powershell
Get-ChildItem -Path "D:\MATEUS\Documentos\GitHub\NAVEGADOR_MTS\src" -Recurse -File | Where-Object { $_.FullName -notmatch "__pycache__" } | ForEach-Object {
    $lines = (Get-Content $_.FullName | Measure-Object -Line).Lines
    if ($lines -gt 150) { Write-Error "VIOLAÇÃO >150 LOC: $($_.FullName) ($lines linhas)" }
}
```

### Passo 2: Executar as Suítes de Testes (Python + Node MV3)
```powershell
Set-Location "D:\MATEUS\Documentos\GitHub\NAVEGADOR_MTS"
python -m compileall -q src entrypoint.py stdio_entrypoint.py
python -m pytest -q
node tests/run_extension_suite.mjs
```

### Passo 3: Sincronizar a Nova Versão SemVer
A versão deve ser idêntica em `src/version.py`, `src/extension/manifest.json` e `installer.iss`:
```powershell
# Definir versão específica (ex.: 2.4.0) ou incrementar patch:
python release_version.py --set 2.4.0
# ou:
python release_version.py --bump patch
```

### Passo 4: Compilar Binários PyInstaller e Instalador Inno Setup
```powershell
.\COMPILAR_INSTALADOR.bat
```
Confirme que o arquivo `dist_installer\NAVEGADOR_MTS_Instalador_v<VERSAO>.exe` foi gerado com sucesso ($>1\text{ MiB}$) e atualize o handoff em `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\01-HANDOFF-VIVO.md`.
