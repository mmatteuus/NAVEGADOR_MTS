# Atualizações do NAVEGADOR MTS

O botão **Atualizações** consulta a release estável configurada e baixa somente
o instalador `.exe` completo. O ZIP da branch e cópia de `src` não são canais
de atualização do executável PyInstaller.

Uma resposta HTTP 404, timeout, JSON inválido, release sem `.exe` ou download
inválido aparece como falha no botão. Isso não significa que o aplicativo está
atualizado. A versão só é aceita quando é numericamente maior que a instalada.

O instalador mantém o AppId e a pasta padrão:
`%LOCALAPPDATA%\Programs\NAVEGADOR MTS`. A sobreposição substitui arquivos do
programa e preserva `%APPDATA%\browser-mcp-mts`, onde ficam logs, credenciais
protegidas e configuração do túnel.

Para gerar uma versão local, execute `COMPILAR_INSTALADOR.bat` e confirme o
arquivo `dist_installer\NAVEGADOR_MTS_Instalador_v<versão>.exe`. Antes de uma
publicação, valide o tamanho, SHA-256, tag, asset e acesso HTTP da release.

Não publique tokens neste repositório. O instalador fecha somente processos
com caminho completo dentro da pasta instalada: desktop, MCP e binários do
túnel. Não há encerramento global por nome.

## Fluxo de release e reparo

O canal principal usa o repositório público atual e cada push para `main`, após
os testes, gera no CI uma versão `2.1.3.<run_number>` (a versão base pode ser
alterada intencionalmente). Cada release precisa conter
os quatro componentes da mesma versão: tag estável, instalador `.exe`,
manifesto da extensão e executável desktop. O CI gera a versão do build no
checkout efêmero, valida esses componentes e publica o asset com o nome
canônico. O botão sempre pede consentimento no popup antes de baixar e iniciar
o instalador. Além da verificação ao iniciar, a janela repete a consulta a
cada hora enquanto o aplicativo permanece aberto; ela apenas exibe o popup e
nunca baixa ou instala sem consentimento.

O nome antigo `mmatteuus/browser-mcp-mts` permanece como redirecionamento para
`mmatteuus/NAVEGADOR_MTS`; por isso instalações 2.1.2 conseguem encontrar a
primeira release depois que ela for publicada. Na verificação de 16/10/2026,
ambos os endpoints `releases/latest` ainda retornavam 404 porque não havia uma
release pública disponível; uma falha HTTP deve continuar visível como falha de
consulta, nunca como aplicativo atualizado.

Para reparar a instalação atual, gere primeiro o instalador 2.1.3 corrigido,
confirme hash e versão, e execute-o sobre `%LOCALAPPDATA%\Programs\NAVEGADOR
MTS`. Depois valide o registro, o executável, a extensão e a preservação de
`%APPDATA%\browser-mcp-mts`. Uma release futura só pode ser considerada pronta
após esse ensaio e a revisão independente do artefato.
