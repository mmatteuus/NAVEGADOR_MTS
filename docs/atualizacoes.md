# 📦 Atualizações, Versionamento e Releases do NAVEGADOR MTS (v2.4.0)

## 1. Como Funciona o Atualizador Oficial (`src/core/updater.py`)

O botão **Atualizações** (e a verificação automática periódica) consulta a release estável oficial no GitHub (`mmatteuus/NAVEGADOR_MTS`) e baixa exclusivamente o instalador completo `NAVEGADOR_MTS_Instalador_v<versão>.exe`.

### Fallback Web Resiliente Contra Rate-Limit HTTP 403 (`src/core/update_web_fallback.py`)
- Caso a API REST pública do GitHub (`api.github.com/repos/mmatteuus/NAVEGADOR_MTS/releases/latest`) retorne erro de limite de requisições sem token (**HTTP 403 Rate Limit**), o atualizador aciona automaticamente o fallback web via redirecionamento público (`https://github.com/mmatteuus/NAVEGADOR_MTS/releases/latest`).
- O fallback identifica a tag estável mais recente, valida o hash `.sha256` quando publicado e baixa o instalador `.exe` correspondente.
- Caso não haja conexão externa, o atualizador também verifica se existe um instalador mais novo já compilado localmente em `dist_installer\`.

---

## 2. Preservação de Dados e Fechamento Seguro de Processos

- O instalador mantém o `AppId` oficial e instala os binários em:
  `%LOCALAPPDATA%\Programs\Navegador MTS`
- A pasta `%APPDATA%\browser-mcp-mts` (onde ficam logs, `tunnel.json` e credenciais criptografadas via DPAPI em `secrets\`) **é 100% preservada** durante qualquer atualização.
- Antes de substituir os arquivos, o script `installer\close_owned_processes.ps1` fecha **exclusivamente** os processos cujo caminho absoluto pertença à pasta instalada (`NAVEGADOR_MTS.exe`, `NAVEGADOR_MTS_MCP.exe`, `tunnel-client.exe`, `cloudflared.exe`), nunca interferindo em processos de outros projetos.

---

## 3. Fluxo Padronizado de Versionamento e Build Local (`v2.4.0`)

Sempre que uma melhoria for implementada no código, gere uma nova versão seguindo estes passos:

```powershell
# 1. Sincronizar a versão em src/version.py, src/extension/manifest.json e installer.iss
python release_version.py --set 2.4.0
# (Ou usar --bump patch / --bump minor / --bump major)

# 2. Executar as suítes de testes Python (444+ testes) e Node MV3
python -m pytest -q
node tests/run_extension_suite.mjs

# 3. Compilar os executáveis PyInstaller e gerar o instalador Inno Setup 6
.\COMPILAR_INSTALADOR.bat
```

O instalador final será gerado em:
`dist_installer\NAVEGADOR_MTS_Instalador_v2.4.0.exe`

---

## 4. Pipeline de CI e Release Automática (`.github/workflows/windows-qa.yml`)

No GitHub Actions, cada push na branch `main`:
1. Executa a validação de sintaxe e a suíte da extensão em Linux (`sintaxe`).
2. Executa os 444+ testes `pytest` e a suíte Node `.mjs` em Windows (`contratos`).
3. No job `release`, executa `prepare_release.py` para estampar `<BASE_VERSION>.<GITHUB_RUN_NUMBER>`, compila o instalador via PyInstaller + Inno Setup, gera o arquivo `.sha256` e publica a release imutável via `publish_release.py`.
