# Destinos por agente — implementação local em validação

Cada conexão MCP inicializada aparece com nome e identificador de sessão. Dois
chats com o mesmo nome continuam sendo agentes distintos. Clientes HTTP precisam
enviar o identificador recebido na inicialização ao chamar ferramentas.

## Guias e sistemas web

1. Conecte os agentes à aplicação.
2. No popup da extensão, escolha o agente correspondente a cada guia permitida.
3. Salve a seleção. Cada agente vê e opera somente suas concessões.

Reatribuir uma guia ou remover a seleção revoga seu acesso anterior. Criar uma
guia por ferramenta não concede acesso automaticamente: o resultado informa que
falta atribuí-la no popup. PWAs abertos como páginas usam esse mesmo caminho;
compatibilidade com cada sistema e com PWAs instalados precisa de validação própria.

O teste real com duas sessões demonstrou digitação concorrente, bloqueio cruzado,
revogação e preservação de campos, foco, seleção e guia ativa em páginas locais.
Isso não equivale à homologação de todo sistema web ou de todo cliente de chat.

## Programas e interface

Em **Destinos → Programas**, escolha o agente e a janela, depois **Atribuir**.
**Revogar** invalida a concessão; reutilizar um identificador de janela não
transfere automaticamente o acesso para outro processo. O controle de computador
continua dependendo da autorização de segurança da aplicação.

`computer_window_action` inspeciona controles, aciona botões/menus e lê ou define
valores quando o aplicativo disponibiliza padrões de acessibilidade compatíveis.
Capturas remotas são limitadas à janela atribuída. Não existe fallback automático
para mouse ou teclado físicos.

**Limitação em aberto:** menus do VS Code foram acionados em um perfil descartável
com acessibilidade ativa, mas a abertura do menu alterou o primeiro plano do Windows.
UIA não garante que o próprio aplicativo preserve o foco. O usuário exige a janela
já aberta; outra instância foi descartada. A política de uso temporário do foco
ou execução de funções equivalentes ainda precisa ser definida. Não reinicie nem
altere o VS Code pessoal automaticamente para ativar esse recurso. Enquanto isso,
menus que exigem expansão retornam FOCUS_REQUIRED; um argumento enviado pelo
agente não pode autorizar a mudança de foco.

## Pastas e arquivos

Em **Destinos → Pastas e arquivos**, escolha um agente e uma pasta. O agente recebe
um identificador de raiz exclusivo e usa caminhos relativos com
`computer_folder_action`: listar, ler, criar arquivo/pasta e gravar texto UTF-8.
O limite de arquivo é 1 MiB; árvores concedidas a agentes diferentes não se sobrepõem.

Para gravar um arquivo existente, envie `expectedVersion` obtido na leitura.
Se o arquivo mudou, a gravação é recusada. Caminhos externos, junctions, reparse
points, hardlinks de arquivos e fluxos alternativos são bloqueados. A escrita usa
o mesmo handle exclusivo da comparação; não há garantia de recuperação contra
queda de energia no meio da gravação. Não há exclusão nem execução de shell.

Esse acesso trabalha no disco. Um buffer ainda não salvo no editor não é o arquivo
em disco; não use a ferramenta para sobrescrever trabalho não salvo.

## Estado da entrega

Alterações locais na branch de trabalho; sem instalação pessoal, publicação ou
release. As evidências e os gates restantes ficam em
[QA da tarefa](tasks/multi-agent-reliability-qa.md).
