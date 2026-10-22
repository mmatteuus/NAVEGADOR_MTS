# NAVEGADOR MTS 2.2.1

## Teclado virtual independente

O teclado do agente agora usa um canal Win32 em segundo plano, endereçado à
janela alvo, sem mover o cursor físico, roubar foco ou misturar modificadores
entre chamadas concorrentes. O modo físico continua disponível somente quando
`background=false` e com autorização explícita no SafetyGate.

O alvo explícito é validado por janela, PID/thread e foco físico antes de cada
lote. Janelas encerradas, handles reutilizados, controles focados pelo usuário
e teclas desconhecidas falham sem fallback.

## Extensão e abas

A extensão 2.2.1 mantém concessões de abas selecionadas no popup em
`chrome.storage.session`. Ações sem `tabId` só funcionam quando há exatamente
uma aba concedida; abas fechadas, trocadas ou não concedidas são rejeitadas.

## Atualização

Para uma instalação existente, use o instalador versionado gerado pelo build.
Em CI, o nome recebe o sufixo da execução, como
`NAVEGADOR_MTS_Instalador_v2.2.1.<run>.exe`. A extensão também pode ser carregada
manualmente em `chrome://extensions` ou `edge://extensions` com a pasta
`extension` instalada, mantendo o modo do desenvolvedor ativo.

O teclado web mantém alvo e caret virtuais por aba/documento, sem usar o foco
do usuário. O popup permite abrir e liberar uma URL HTTP(S) inativa ou liberar
uma ou várias abas pessoais já abertas. Sem seleção inequívoca, a ação falha.
Rich text, atalhos que exigem seleção real e controles nativos fora da rota
Win32 não são prometidos; `PostMessageW` confirma somente enfileiramento, não
entrega universal ao controle.
