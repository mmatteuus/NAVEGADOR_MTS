# 📐 07. Guia de Modularidade e Boas Práticas de Código

## 1. O Mandamento: Arquivos Pequenos e Foco Único

A pedido explícito do usuário, a base de código do **BROWSER MTS** rejeita terminantemente arquivos monolíticos ou funções gigantescas. Cada componente deve ser estruturado de forma cirúrgica, como se tivesse sido esculpido manualmente pelo desenvolvedor com o máximo de clareza:

> 📌 **Regra de Ouro**: Nenhum arquivo deve ultrapassar **150 linhas de código**. Se um arquivo começar a crescer demais, ele deve ser dividido em sub-módulos com responsabilidades bem definidas.

---

## 2. Padrão de Documentação e Comentários nos Arquivos

Todo arquivo criado no projeto deve seguir um padrão uniforme de documentação em **Português do Brasil**:

```typescript
/**
 * @file mouse-controller.ts
 * @description Módulo responsável pelo controle do cursor do mouse no Windows.
 * 
 * Responsabilidades:
 * - Movimentação absoluta e relativa do cursor.
 * - Despacho de eventos de clique simples, duplo e arrasto.
 * - Tratamento de escala DPI para precisão de pixels.
 * 
 * Cuidados de Segurança:
 * - Deve sempre consultar o `security-gate.ts` antes de emitir qualquer evento.
 */

import { securityGate } from './security-gate';
import { logger } from '../common/logger';

/**
 * Move o cursor do mouse até as coordenadas informadas.
 * 
 * @param x - Posição horizontal na tela em pixels.
 * @param y - Posição vertical na tela em pixels.
 * @throws {SecurityError} Caso o controle do computador esteja desativado.
 */
export async function moveMouse(x: number, y: number): Promise<void> {
  // 1. Validação obrigatória da trava de autorização
  if (!securityGate.isAuthorized()) {
    logger.warn('Tentativa de mover mouse bloqueada pela trava de segurança.');
    throw new Error('ERRO_SEGURANCA: Controle do computador desativado pelo usuário.');
  }

  // 2. Execução da movimentação nativa
  // ... lógica compacta e clara ...
}
```

---

## 3. Filosofia "Pensar à Frente" (Defensive Engineering)

Ao desenvolver cada função, o programador deve analisar preventivamente: **"Qual outro erro ou problema pode acontecer em cascata com a resolução deste problema atual?"**

| Ação Primária | Erro em Cascata em Potencial | Solução Preventiva Obrigatória |
| :--- | :--- | :--- |
| Criar conexão WebSocket | A porta `3456` já estar em uso por instância antiga | Testar porta antes de subir e encerrar processos órfãos com aviso elegante |
| Agente clica em elemento web | O elemento sair da tela antes do clique ser processado | Re-validar se o elemento ainda existe no DOM e tentar novamente em 200ms |
| Usuário tranca o Windows (`Win+L`) | O screenshot falhar por falta de sessão desktop ativa | Capturar a exceção e avisar o agente que a sessão do Windows está bloqueada |
| Agente digita texto longo | Teclas ficarem "presas" se a conexão cair no meio | Disparar rotina de reset de teclas (`releaseAllKeys`) em qualquer erro ou timeout |
| Múltiplos comandos simultâneos | Condição de corrida (Race condition) de ações concorrentes | Fila sequencial (Queue) garantindo que um clique termine antes do próximo começar |

---

## 4. Estrutura de Tratamento de Erros

1. **Nunca Deixar Exceções Não Tratadas (`uncaughtException`)**: Todo processo deve capturar erros globais, registrar no log com máscara de segredos e manter a estabilidade do sistema.
2. **Padrão de Retorno Tipado**: Funções críticas retornam objetos estruturados de resultado `{ success: boolean, data?: T, error?: string }` em vez de disparar falhas fatais que derrubem o app.
3. **Descarte Limpo de Recursos (`Cleanup`)**: Todos os timers (`setInterval`, `setTimeout`), listeners de eventos e processos filhos devem ser devidamente limpos no ciclo de vida de encerramento (`dispose()`).

---

## 5. Resumo da Documentação

Com este conjunto de diretrizes, o **BROWSER MTS** garante:
- Código legível, didático e manutenível por qualquer humano ou agente.
- Robustez contra falhas de rede, queda de extensões e suspensão do sistema operacional.
- Visual moderno e nativo do Windows 11 com foco na facilidade e segurança do usuário.

