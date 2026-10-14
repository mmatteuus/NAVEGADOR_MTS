# 🌐 BROWSER MTS & COMPUTER USE — Documentação Oficial do Sistema

> **Visão Geral**: Sistema unificado de automação para Agentes de IA com visual moderno nativo para Windows 11, combinando controle total do navegador via extensão Chrome/Edge e automação do computador (mouse, teclado e tela) protegida por chave de autorização do usuário e mecanismo de emergência (Kill Switch).

---

## 📚 Índice da Documentação

Para facilitar a leitura, navegação e manutenção por qualquer desenvolvedor ou agente, a documentação está dividida em módulos temáticos objetivos:

| Documento | Assunto Principal | Conteúdo Abordado |
| :--- | :--- | :--- |
| **[01. Visão Geral e Arquitetura](01-VISAO-GERAL-E-ARQUITETURA.md)** | Arquitetura do Sistema | Estrutura modular, diagrama de blocos, fluxo end-to-end e tecnologias adotadas. |
| **[02. Resiliência e Reconexão](02-RESILIENCIA-E-RECONEXAO.md)** | Diagnóstico e Auto-Cura | Causa-raiz das desconexões da versão legada, protocolo de heartbeat e recuperação em ≤ 5s. |
| **[03. Extensão do Navegador](03-EXTENSAO-NAVEGADOR.md)** | Extensão Manifest V3 | Service worker, popup com design moderno, injeção de scripts e ferramentas de automação web. |
| **[04. Automação do Computador](04-CONTROLE-COMPUTADOR-COMPUTER-USE.md)** | Computer Use & Segurança | Controle de mouse, teclado e tela, Trava de Autorização física e Kill-Switch de pânico. |
| **[05. Servidor MCP e Protocolo](05-SERVIDOR-MCP-E-TRANSPORTE.md)** | Protocolo MCP e Túneis | Catálogo unificado de ferramentas MCP, compatibilidade com OpenAI Tunnel, Claude e stdio. |
| **[06. Interface Windows 11 e UX](06-INTERFACE-WINDOWS-11-UX.md)** | Experiência e UI Nativa | Design Fluent Win11, bandeja do sistema (System Tray), notificações nativas e temas claro/escuro. |
| **[07. Guia de Código e Boas Práticas](07-GUIA-DE-MODULARIDADE-E-BOAS-PRATICAS.md)** | Padrões de Desenvolvimento | Regra de arquivos pequenos (< 150 linhas), modularidade cirúrgica e comentários didáticos. |
| **[08. Armazenamento Local e Privacidade](08-ARMAZENAMENTO-LOCAL-E-PRIVACIDADE.md)** | Privacidade e Segurança | Política 100% Local-First, DPAPI e zero-telemetria para máxima adesão e confiança. |

---

## 🎯 Princípios Fundamentais do Projeto

1. **Arquitetura em Arquivos Pequenos**: Nada de arquivos monolíticos. Cada arquivo possui uma responsabilidade única, facilitando testes, entendimento e evolução.
2. **Código Altamente Comentado**: Cada módulo é documentado internamente em português, explicando *o que faz*, *por que faz* e *quais cuidados tomar*.
3. **Segurança em Primeiro Lugar**: O agente de IA nunca pode tomar o controle do sistema operacional sem que o usuário tenha ativado explicitamente o interruptor de autorização.
4. **Resiliência Extrema**: Reconexão silenciosa e imediata para que nem o agente nem o usuário precisem reabrir programas caso ocorra oscilação na rede ou no navegador.
5. **Pensar à Frente**: Tratamento preventivo de deadlocks, conflitos de portas, múltiplos monitores, suspensão do Windows e concorrência de eventos.

