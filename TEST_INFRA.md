# 🧪 Infraestrutura e Estratégia de Testes Automatizados (TEST_INFRA)

Este documento descreve a metodologia, arquitetura de validação em camadas (Tiers 1 a 4), diretrizes de isolamento de produção e comandos de execução da suíte de testes do **BROWSER MTS**.

---

## 1. Princípios Fundamentais e Diretrizes

1. **Modularidade Extrema**: Todos os arquivos de teste sob a pasta `tests/` possuem rigorosamente **menos de 150 linhas de código**, com responsabilidade única e focada.
2. **Código Didático em Português do Brasil**: Nomenclatura descritiva, documentação de cabeçalho e comentários técnicos explicando cada assertiva e contrato de interface.
3. **Isolamento Absoluto de Produção**:
   - A suíte monitora via sentinela (`conftest.py`) os PIDs da instância de produção em `C:\Users\MATEUS\browser mcp mts\` (`17892`, `8928`, `6548`, `6052`). Nenhum desses processos é finalizado ou alterado.
   - Os testes de rede utilizam portas dinâmicas e isoladas (ou a porta de desenvolvimento `3456`), nunca conflitando com a porta `9009` da produção.
4. **Garantia de Zero Órfãos e Zero Portas Presas**:
   - Todos os processos filhos criados nos testes são gerenciados pelo `ProcessSupervisor` com encerramento de árvore via `psutil`.
   - Todos os sockets utilizam `SO_REUSEADDR` para evitar retenção em `TIME_WAIT`.

---

## 2. Matriz de Qualidade em Camadas (Tiers 1 a 4)

```text
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 4: Estabilidade Contínua, Soak Test e Prevenção de Vazamentos    │
│ - 0 vazamentos de memória (RAM estável em repouso < 60 MB)             │
│ - 0 descritores/handles acumulados no Windows                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│ TIER 3: Engenharia de Caos, Injeção de Falhas e Auto-Cura (<= 5s)      │
│ - Morte abrupta de processo filho -> Supervisor reinicia em <= 2s      │
│ - Queda de WebSocket simulada -> Detecção de pulso e reconexão em <= 5s│
│ - Estresse: 20 ciclos de Start/Stop com 0 processos órfãos e 0 portas  │
│ - Kill-Switch de pânico: 3 toques em ESC (< 1.2s) aborta na hora       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│ TIER 2: Integração de Módulos e Contratos de Protocolo                 │
│ - Servidor MCP Stdio e WebSocket Bridge (porta 3456)                   │
│ - Buffer circular com retenção por até 15 segundos (TTL)               │
│ - Schemas JSON formais para browser_* e computer_*                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│ TIER 1: Testes Unitários de Segurança e Lógica Central                 │
│ - SafetyGate: Política Fail-Closed (Default-Deny) e trilha de auditoria│
│ - HeartbeatManager: 3s ping, 2s timeout, 2 falhas = reconexão          │
│ - Backoff Exponencial com teto estrito em 5.0 segundos e jitter        │
│ - DPAPI do Windows e sanitização de segredos em logs                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Catálogo de Arquivos da Suíte de Testes

| Arquivo de Teste | Linhas (LOC) | Responsabilidade Principal |
| :--- | :--- | :--- |
| `tests/conftest.py` | < 75 linhas | Sentinela de integridade da produção, portas dinâmicas e rastreador de limpeza de processos. |
| `tests/test_harness.py` | < 80 linhas | Utilitários de apoio: checagem de portas, supervisor dummy e cliente mock da extensão MV3. |
| `tests/test_safety_gate.py` | < 100 linhas | Trava de segurança Fail-Closed, concessão/revogação, Kill-Switch (3x ESC) e trilha de auditoria. |
| `tests/test_mcp_protocol.py` | < 100 linhas | Contratos JSON-RPC 2.0 do MCP (initialize, ping, tools/list, tools/call) e roteador com trava. |
| `tests/test_mcp_ws_bridge.py` | < 105 linhas | Comunicação bidirecional WebSocket Bridge, timeouts, erros e handshakes da extensão. |
| `tests/test_resilience.py` | < 105 linhas | Injeção de falhas (morte de processo, perda de pulso) com auto-cura comprovada em <= 5 segundos. |
| `tests/test_stress_cycles.py` | < 75 linhas | Teste de estresse com 20 ciclos consecutivos de start/stop (0 órfãos e 0 portas retidas). |

---

## 4. Comandos de Execução dos Testes

### Executar a Suíte Completa
Para rodar todos os testes automatizados com relatório detalhado:
```powershell
python -m pytest tests/ -v
```

### Executar por Módulo Específico

1. **Trava de Segurança e Kill-Switch (Safety Gate)**:
   ```powershell
   python -m pytest tests/test_safety_gate.py -v
   ```

2. **Protocolo MCP e WebSocket Bridge**:
   ```powershell
   python -m pytest tests/test_mcp_protocol.py -v
   ```

3. **Resiliência, Injeção de Falhas e Auto-Cura (<= 5s)**:
   ```powershell
   python -m pytest tests/test_resilience.py -v
   ```

4. **Estresse: 20 Ciclos Consecutivos de Start/Stop**:
   ```powershell
   python -m pytest tests/test_stress_cycles.py -v
   ```

### Executar com Saída Silenciosa / Resumo
```powershell
python -m pytest tests/ -q
```

---

## 5. Critérios de Aprovação e Validação

- **Taxa de Sucesso**: 100% dos testes devem passar (`PASSED`), sem falhas (`FAILED`) ou erros de execução (`ERROR`).
- **Tempo de Recuperação (Self-Healing)**: $\le 5.0$ segundos comprovados por medições de cronômetro nos testes de resiliência.
- **Processos Ativos Pós-Teste**: 0 processos filhos residuais nos testes de estresse e supervisão.
- **Isolamento de Produção**: Os PIDs originais (`17892`, `8928`, `6548`, `6052`) permanecem intocados e respondendo no Windows.
