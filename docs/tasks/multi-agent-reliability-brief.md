# Confiabilidade e destinos por agente

Data: 2026-10-25. Base inspecionada: 9cfceb7, árvore inicialmente limpa.
Execução: Codex no VS Code, quatro especialistas nativos e coordenador.
Objetivo ativo: corrigir falhas da extensão; sincronizá-la automaticamente com
atualizações do desktop; atribuir guias e programas a agentes simultâneos;
manter entrada do usuário independente. Exemplos: chat em uma guia controlando
outra guia/PWA, VS Code, Explorador, pastas e arquivos.

## Especificação consolidada — SPEC DONE

Diagnósticos de quatro especialistas concluídos antes da implementação.
O popup atual concede globalmente e o primeiro agente assume a guia. Teclado
Win32 mantém alvo global enquanto mouse já possui coordenadas por sessão.
Atualização recarrega a pasta de origem; uma cópia externa não recebe arquivos.
Ainda faltam reproduções específicas para classificar falhas frequentes.

1. Diretório de agentes originado no transporte MCP, com nome e identificador
   distinguíveis; nenhuma identidade fornecida em argumentos substitui a sessão.
2. Popup permite escolher agente e guias explicitamente. Gravação serializada,
   sem revogar guias de outro agente. Atribuição persistida em storage.session.
   Reatribuição humana revoga o proprietário anterior e revalida comandos na
   execução; nunca usar guia ativa como fallback. Listagem filtrada por sessão.
3. Nova guia só recebe concessão por ação explícita do usuário no popup.
   Compatibilidade de concessão sem destinatário será visível como primeiro
   agente, sem sobrepor atribuições explícitas. Fechar/substituir revoga acesso.
4. Reconexão recuperável, nenhuma execução duplicada automática de ações, erros
   assíncronos tratados, respostas vinculadas à conexão de origem. Trocas de
   versão só recarregam em ponto seguro e não entram em loop.
5. Instalador entrega extensão na pasta estável. Comparar versão carregada,
   versão disponível e confirmação pós-recarga. Estado desatualizado não pode
   ser apresentado como atualizado. Validar substituição/reload em perfil
   descartável real. Cópia externa exige migração explícita para pasta gerenciada.
6. UI desktop permite atribuir programa a agente. Registrar HWND/PID/thread,
   impedir outro agente, revalidar alvo e revogação durante ações. Teclado e
   mouse virtuais por sessão; SafetyGate permanece obrigatório. Nenhum fallback
   físico automático. Ações físicas não satisfazem isolamento solicitado.
7. Programas modernos: implementar rota semântica UI Automation por padrões
   suportados e validar VS Code/Explorador. Controles incompatíveis exigem
   solução de isolamento adicional; não declarar escopo completo por rejeitá-los.

## Grafo e propriedade de arquivos

- ROOT: diretório Python de sessões/protocolo, integração, documentação.
- ASSIGN: tab_access/session_registry/extension_identity, popup e service_worker.
- STABILITY: ws_client, command_dispatcher, tab_manager, content e novos módulos.
- UPDATE: política de reload, empacotamento/instalador, novo módulo ws_update;
  alteração de imports em ws_client via STABILITY, handshake via ROOT.
- DESKTOP: computer, schemas/dispatch de computer, UI de programas.
- QA: revisão cruzada após implementação, suítes integradas e ensaios reais
  separados; especialistas não aprovam sozinhos a própria implementação.

## Evidência e limites

Reproduzir regressões; testar duas sessões concorrentes, reatribuição, reinício
do worker, perda de conexão, troca de versão, PID/HWND reutilizado e revogação.
E2E em navegador/perfil temporário com páginas locais; Win32 em janelas próprias
ocultas. Não executar testes que movam entrada física do usuário. Registrar
comandos, resultados e limitações. Arquivos alterados abaixo de 150 LOC.
Não alterar legado, credenciais, instalação pessoal, dados ou processos do
usuário. Sem commit/push/release nesta autorização. Publicação e instalação real
ficam como etapas distintas; testes locais não provam uso no cliente final.
Parar antes de mutações externas não autorizadas ou violação de isolamento.
Meta só concluída quando todos os requisitos tiverem evidência atual.

## Extensão da especificação: pastas e arquivos — SPEC DONE

Exemplos esclarecidos pelo usuário: PWA, VS Code, pastas e arquivos. Enquanto
se valida a automação de interface, adicionar acesso direto a arquivos dentro
de pasta escolhida pela UI humana. Não confundir disco com buffer não salvo
do VS Code; suporte a menus/buffers permanece item separado do objetivo.

FILE-1: registro exclusivo de raiz canônica por sessão, concessão/revogação só
na UI. MCP lista apenas raízes já concedidas; não expõe seletor nem auto-grant.
FILE-2: listar/ler/criar pasta/criar arquivo/gravar texto, com limites de tamanho,
path relativo, bloqueio de escapes, ADS, caminhos reservados, UNC e reparse
points. Validar handle final Win32 e identidade da raiz; revogação por geração.
FILE-3: escrita exige versão recebida da leitura; impedir sobrescrita concorrente
por abertura exclusiva/validação de handle e conflito explícito. Não adicionar
execução de shell ou exclusão recursiva. Não afirmar atomicidade de substituição
se houver intervalo destravado entre validação e troca.
FILE-4: testes reais em diretório temporário, dois agentes e terceiros alterando
arquivo, junction/reparse point, revogação, raiz substituída. Documentar limite
de alterações não salvas no editor. Não tocar em arquivos pessoais para testar.
Owner final: ROOT (folder_*, integração e painéis); STABILITY faz QA independente.

## Menus e botões — janela existente obrigatória

O usuário confirmou explicitamente que precisa dos menus e botões do VS Code.
Em perfil descartável com acessibilidade ativa, UIA descobriu o workbench e abriu
Help com submenu real. A abertura do menu Electron mudou o foreground; portanto
esse caminho não satisfaz sozinho a independência de foco no desktop compartilhado.
O usuário respondeu: "Exatamente a janela já aberta". Não criar outra instância
ou ambiente gráfico como solução. Pesquisa de APIs oficiais confirmou que uma
extensão companheira pode executar comandos internos, mas não oferece uma API
universal de clique em menus nem correlação pública direta com HWND. Não instalar
extensão no VS Code pessoal nem reiniciá-lo implicitamente.
Pergunta pendente: aguardar liberação humana do foco para abrir menus, executar
funções equivalentes sem abrir visualmente o menu, ou permitir foco temporário.
Não assumir consentimento para mudar foco a partir da escolha da janela existente.
