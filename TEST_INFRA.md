# 🧪 Infraestrutura e Estratégia de Testes Automatizados E2E (TEST_INFRA)

Este documento estabelece a metodologia formal de testes Opaque-Box E2E, a arquitetura de validação em 4 Tiers, as diretrizes de isolamento de produção e os comandos de execução da suíte de testes do **NAVEGADOR MTS (v2.2.0)**.

---

## 1. Princípios Fundamentais e Diretrizes

1. **Modularidade e Limite Estrito de Código**:
   - Cada arquivo de teste na pasta `tests/` possui rigorosamente **$\le 150$ linhas de código (LOC)**.
   - Responsabilidade única e desacoplada por suíte/tier.
2. **Abordagem Opaque-Box (Caixa Opaca)**:
   - Os testes exercitam a aplicação estritamente através de suas interfaces públicas e contratos de protocolo (JSON-RPC 2.0 do MCP, schemas JSON formais, WebSocket Bridge e envelopes de resposta).
   - Validação centrada em entradas e saídas observáveis, sem acoplamento a implementações internas voláteis.
3. **Isolamento de Produção e Segurança Absoluta**:
   - Sentinela de integridade (`tests/conftest.py`) monitora os PIDs de produção (`PROD_PIDS = [17892, 8928, 6548, 6052]`). Nenhum processo legado é interrompido.
   - Alocação de portas dinâmicas via socket temporário (`dynamic_port`), proibindo uso da porta de produção `9009`.
   - Política Fail-Closed (Default-Deny) no `SafetyGate` e interrupção imediata via `EmergencyKillSwitch`.
4. **Isolamento de Segundo Plano (Background & Zero Focus Stealing)**:
   - Garantia de que operações do agente no navegador operam com `active: false` e `focusWindow: false`.
   - Garantia de que ações virtuais no Windows não sequestram o cursor físico do usuário (`GetCursorPos`).

---

## 2. Metodologia de Teste Opaque-Box

A suíte adota quatro técnicas formais de projeto de testes:

| Metodologia | Aplicação no NAVEGADOR MTS |
| :--- | :--- |
| **Category-Partition** | Decomposição sistemática dos parâmetros de entrada dos schemas MCP (`browser_*` e `computer_*`) em classes de equivalência válidas e inválidas. |
| **Boundary Value Analysis (BVA)** | Testes exaustivos nas fronteiras de coordenadas `(x, y)`, qualidades de imagem (1 a 100), timeouts, strings vazias e payloads Unicode extremos (ABNT2). |
| **Pairwise (All-Pairs Testing)** | Combinação ortogonal de pares de parâmetros entre ferramentas de browser e computer para detectar defeitos originados por interações cruzadas. |
| **Workload / Scenario Testing** | Simulação de fluxos de trabalho reais de agentes autônomos executando tarefas completas em background de ponta a ponta. |

---

## 3. Matriz de Qualidade em Camadas (4 Tiers)

```text
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 4: Real-World Application Scenarios (Mínimo de 5 Cenários)        │
│ - Extração de dados e documentação em background sem roubo de foco     │
│ - Preenchimento sequencial de formulário com inspeção ARIA             │
│ - Automação híbrida segura (Browser + Desktop) com SafetyGate          │
│ - Intervenção de emergência por Kill-Switch (3x ESC) abortando fluxo   │
│ - Resiliência e recuperação transparente a oscilações de rede          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│ TIER 3: Cross-Feature Combinations (Pairwise Testing)                  │
│ - Navegação background (active=False) combinada com captura por tabId  │
│ - Abertura de aba isolada + Digitação e clique sintético no DOM        │
│ - Status autorizado + Ação de mouse virtual background Win32           │
│ - Execução concorrente de inspeção de abas e verificação de segurança  │
│ - Transições de estado da trava SafetyGate durante fluxos de comando   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│ TIER 2: Boundary & Corner Cases (>= 5 Casos por Funcionalidade)        │
│ - Coordenadas extremas (negativas, zero, limites de resolução)         │
│ - Delimitadores de qualidade (quality=1, quality=100, fora de faixa)   │
│ - Strings vazias, URLs malformadas, caracteres de controle e ABNT2     │
│ - Rejeição fail-closed quando SafetyGate desautorizado                 │
│ - Schemas ausentes de parâmetros obrigatórios e tipos incompatíveis    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│ TIER 1: Feature Coverage (>= 5 Casos por Funcionalidade)               │
│ - Navegação e gerenciamento de abas (navigate, list, new, switch, close)│
│ - Interações DOM/CDP (click, type, hover, scroll, press_key)           │
│ - Observação e dados (screenshot Base64, snapshot ARIA, evaluate_js)   │
│ - Controle desktop sob SafetyGate (status, mouse_action, keyboard)     │
│ - Ciclo JSON-RPC 2.0 (initialize, ping, tools/list, tools/call)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Catálogo dos Arquivos de Teste E2E

| Arquivo de Teste | LOC | Tier / Responsabilidade |
| :--- | :--- | :--- |
| `tests/test_e2e_tier1_browser.py` | $\le 150$ | **Tier 1**: Cobertura de funcionalidades do navegador (`browser_*`) |
| `tests/test_e2e_tier1_computer.py` | $\le 150$ | **Tier 1**: Cobertura de funcionalidades desktop (`computer_*`) |
| `tests/test_e2e_tier2_boundaries.py` | $\le 150$ | **Tier 2**: Testes de fronteira, valores extremos e rejeição fail-closed |
| `tests/test_e2e_tier3_combinations.py` | $\le 150$ | **Tier 3**: Combinações cruzadas pairwise entre browser e desktop |
| `tests/test_e2e_tier4_scenarios.py` | $\le 150$ | **Tier 4**: Cenários de uso real do agente em background |

---

## 5. Comandos de Execução

### Executar Toda a Suíte E2E
```powershell
python -m pytest tests/test_e2e_*.py -v
```

### Executar por Tier Específico
```powershell
# Tier 1 - Cobertura de Funcionalidades
python -m pytest tests/test_e2e_tier1_browser.py tests/test_e2e_tier1_computer.py -v

# Tier 2 - Limites e Casos de Borda
python -m pytest tests/test_e2e_tier2_boundaries.py -v

# Tier 3 - Combinações Ortogonais Pairwise
python -m pytest tests/test_e2e_tier3_combinations.py -v

# Tier 4 - Cenários Reais de Aplicação
python -m pytest tests/test_e2e_tier4_scenarios.py -v
```

### Executar Toda a Suíte do Projeto (E2E + Unidade + Regressão)
```powershell
python -m pytest -q
```

---

## 6. Critérios de Aceite e Aprovação

- **100% de Aprovação**: 0 falhas e 0 erros em todos os testes E2E.
- **Conformidade de Tamanho**: 100% dos arquivos de teste $\le 150$ LOC.
- **Sentinela de Produção Intacta**: Os PIDs em `PROD_PIDS` permanecem ativos e inalterados.
- **Fail-Closed Imutável**: Nenhuma ação `computer_*` é executada sem autorização explícita.
