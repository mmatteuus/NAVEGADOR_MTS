# Teclado e guias do agente

O teclado virtual usa um campo e uma posição de texto próprios, sem mover o
foco, o cursor físico ou a seleção de texto do usuário. Funciona em guias
liberadas pelo usuário, inclusive guias pessoais já abertas e autenticadas.

## Escolher uma ou várias guias

1. Abra o popup da extensão **NAVEGADOR MTS**.
2. Em **Abas permitidas ao agente**, marque as guias desejadas.
3. Clique em **Salvar seleção**. Desmarcar e salvar retira o acesso.
4. Para uma página ainda não aberta, informe seu endereço HTTP/HTTPS em
   **Abrir URL e liberar** e clique em **Abrir e liberar**. A nova guia abre em
   segundo plano e se soma às permitidas.
5. **Limpar** retira todas as permissões de guias.

A seleção vale para a guia inteira, inclusive quando ela navega para outro
endereço. Fechar a guia retira sua permissão. Reiniciar o navegador, recarregar
ou atualizar a extensão exige selecionar novamente; reiniciar somente o
service worker preserva a seleção da sessão. Nenhuma guia começa liberada.

O agente pode listar as guias e seus IDs. Quando há várias permitidas, deve
enviar `tabId` em cada ação. Com apenas uma permitida, pode omiti-lo. A guia
ativa do usuário nunca é escolhida automaticamente. Abrir uma guia por comando
do agente não concede acesso a ela; a concessão pertence ao usuário no popup.

## Usar o teclado

Informe `selector` ou `ref` no `browser_type`, ou clique antes no campo do
agente com `browser_click`. Chamadas posteriores na mesma página usam o último
alvo do agente. `browser_press_key` também aceita `selector` ou `ref`.

Exemplo: `browser_type` com `{"tabId":123,"selector":"#busca","text":"produto"}`.
O ID deve corresponder a uma guia que você liberou. Para limpar antes de
digitar, use `clearFirst: true`; para enviar o formulário, `submit: true`.

Você pode continuar digitando em outro campo, na mesma guia ou em outra.
Se o agente tentar escrever no campo que você está usando, a operação retorna
`TARGET_IN_USE`. Ela não muda o foco para contornar essa proteção.

Campos de texto, textarea e contenteditable simples são suportados. Editores
ricos com formatação HTML e atalhos incompatíveis retornam erro; não há
fallback para teclado físico, clipboard ou captura do foco. Eventos virtuais
não equivalem a eventos físicos confiáveis para todos os sites. Páginas internas
protegidas do navegador não são destinos de automação da extensão.

## Teclado do Windows

`computer_keyboard_action` mantém `background: true` como padrão e continua
dependendo da autorização de **Controle do Windows** e do kill-switch.
Um `hwnd` explícito fixa o destino do teclado; sem alvo explícito prévio, o
destino segue o cursor virtual, preservando o fluxo mover/clicar/digitar.
O envio é serializado e interrompido se a autorização for retirada, o alvo
desaparecer ou o usuário passar a usar o mesmo controle.

O Windows informa que a mensagem foi enfileirada, não que qualquer aplicativo
arbitrário a aceitou. Controles que exigem entrada física podem não responder.
`background: false` preserva o modo físico anterior e pode interferir na entrada
do usuário; ele precisa ser solicitado explicitamente.

## Ativação local

Se a extensão já foi carregada a partir de `src/extension` deste checkout,
recarregue-a na página de extensões do Chrome/Edge. Recarregue também as páginas
abertas para substituir os scripts antigos. Depois selecione as guias no popup.
Para carregar este checkout pela primeira vez, use **Carregar sem compactação**
e escolha `src/extension`.

As mudanças Python exigem iniciar o aplicativo a partir deste código ou gerar
um novo instalador. Editar o checkout não modifica um executável já instalado.
O trabalho não publica release nem substitui automaticamente a instalação.

## Verificação reproduzível

- Unitários: `python -m pytest -q tests/test_keyboard_background_isolation.py
  tests/test_agent_keyboard_contract.py`.
- Win32 real, controles próprios ocultos: `python tests/keyboard_native_probe.py`.
- Extensão: `node tests/test_keyboard_virtual_isolation.mjs` e
  `node tests/test_agent_tab_policy.mjs`.
- Integração real: `node tests/test_keyboard_browser_e2e.mjs`. Requer Playwright
  disponível; `PLAYWRIGHT_MODULE` pode indicar o pacote local e `QA_CHROMIUM` o
  executável Chromium. Usa perfil descartável, portas livres e páginas loopback.
