# NAVEGADOR MTS 2.3.3

## Melhorias

- Escolha explícita do agente responsável por cada guia no popup da extensão.
- Agentes simultâneos com isolamento de guias, comandos e respostas.
- Reconexão mais robusta, sem repetir automaticamente ações mutáveis.
- Recarga da extensão após atualização do aplicativo, aguardando comandos em
  execução e confirmando a versão carregada, sem ciclos repetidos de recarga.
- Painel Destinos para atribuir uma janela aberta ou uma pasta a cada agente.
- Operações em arquivos limitadas à pasta autorizada, com proteção contra
  sobrescrita de alterações concorrentes e caminhos que escapam da concessão.
- Teclado e mouse em segundo plano vinculados à janela atribuída por sessão.
- Controles compatíveis com UI Automation e revogação explícita de acesso.
- Interface Fluent e melhorias de acessibilidade e navegação pelo teclado.
- Correção da validação de identidade: argumentos de ferramentas não podem
  substituir a identidade fornecida pelo transporte MCP.

## Atualização de instalações existentes

O canal de atualização distribui o instalador completo e seu checksum SHA-256.
A versão publicada inclui o número da execução do workflow: `2.3.3.<execução>`.
O aplicativo verifica atualizações ao iniciar e periodicamente; o usuário
confirma o download e a instalação pelo aviso ou pela tela Atualizações.

A extensão acompanha a atualização quando carregada da pasta gerenciada pelo
instalador. Extensões carregadas de cópias externas precisam ser apontadas para
a pasta instalada. Falhas de recarga ou divergências de versão são informadas.

## Limites preservados

Menus do VS Code que exigem foco continuam bloqueados com `FOCUS_REQUIRED`.
Esta versão não concede permissão implícita para tomar o foco do usuário.
O acesso a arquivos opera no disco e não altera buffers ainda não salvos.
A validação usa ambientes descartáveis e não comprova todos os programas,
PWAs ou clientes de IA. Publicação não significa instalação automática em
todos os computadores; cada usuário confirma a atualização disponível.
