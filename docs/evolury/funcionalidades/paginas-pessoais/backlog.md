# Páginas pessoais — backlog

Plano aprovado em 19/08/2026. Três fases, cada uma publicável sozinha.
Especificação em [especificacao.md](especificacao.md), decisões no
[ADR 0015](../../decisoes/0015-paginas-pessoais.md).

## F1 — A página pessoal

- [x] F1.1 `PageSerializer.create` aceita contexto sem projeto: com projeto cria
      a linha em `ProjectPage` como sempre; sem projeto pega o workspace do
      contexto e não cria nada
- [x] F1.2 `PersonalPagePermission` — a regra é o dono, e nega com **404 e não
      403**. Papel de workspace não entra: administrador não lê caderno pessoal
- [x] F1.3 API sob `my-tasks/pages/`, o mesmo namespace das etapas: listar,
      criar, ler, editar, bloquear, arquivar, excluir, duplicar, descrição
      binária e versões
- [x] F1.4 `live`: tipo de documento `personal_page` e serviço que só troca o
      caminho base. Todos os pontos passam pelo mesmo `getPageService`
- [x] F1.5 `EPageStoreType.PERSONAL`, store, adaptador de `BasePage` e serviços
      no web
- [x] F1.6 Rotas `my-tasks/pages` e `my-tasks/pages/:pageId`, com o editor fora
      do layout de Minhas tarefas
- [x] F1.7 Abas Tarefas/Páginas na barra secundária. Foram para lá porque só ela
      tem `!py-0` — no cabeçalho principal o sublinhado da aba ativa não
      encostava na base. É também onde vivem as abas dos projetos
- [x] F1.8 `PagesListHeaderRoot` passa a receber a navegação da esquerda e ações
      extras à direita, em vez de montar as abas de projeto por conta própria
- [x] F1.9 Testes de contrato com defeito reintroduzido em cada regra, **um de
      cada vez**

**O que a tela ensinou:** a lista nasceu vazia com as páginas existindo, porque
`filterPagesByPageType` decide "privada" pelo campo `access` e página pessoal
nasce com `access=0`. Página pessoal não tem público/privado — o store passou a
ter o próprio filtro, ativa x arquivada.

## F2 — Compartilhar

- [x] F2.1 Modelo `PageShare` (workspace, página, com quem, papel) e migração
      0146, com constraint parcial única em (página, pessoa)
- [x] F2.2 Endpoints de compartilhamento e a aba **Compartilhado comigo**
- [x] F2.3 Permissão por papel, decidida **pelo método HTTP**: GET para os três,
      PATCH para dono e "pode editar", POST/DELETE só para o dono — que nesta
      API são bloquear, arquivar, duplicar, excluir e compartilhar
- [x] F2.4 A trava de página de projeto saiu **estrutural**: a rota pessoal
      resolve com `~Exists(ProjectPage...)`, então compartilhar página de
      projeto não é recusado — ela não existe por ali, e a resposta é 404
- [x] F2.5 Modal de compartilhamento no menu de ações da página
- [x] F2.6 Testes (18), com defeito reintroduzido um de cada vez

**O que a tela ensinou:** o `<select>` de pessoa precisa nascer com string
vazia, não `undefined` — o Combobox de baixo mantém um input escondido, e sair
de "sem valor" para um valor faz o React acusar troca de não-controlado para
controlado. E "Compartilhado comigo" não pode mostrar os controles de tarefa nem
o botão de criar página: é leitura do que é dos outros.

Saíram junto três rótulos que ainda estavam em inglês no menu da página —
"Lock", "Archive" e "Move".

## F3 — Mover

- [x] F3.1 Mover pessoal → projeto e projeto → pessoal, só pelo dono. No sentido
      de ida também é preciso poder criar página no destino — convidado não pode
- [x] F3.2 Aviso antes de mover, com a **contagem vinda do servidor**: "1 pessoa
      perde o acesso: no projeto, quem manda é o projeto"
- [x] F3.3 "Mover para um projeto" na página pessoal e "Mover para Minhas
      tarefas" na de projeto, os dois só para o dono
- [x] F3.4 Testes (23 no total), com defeito reintroduzido um de cada vez

**Restrição da volta:** só recolhe página que esteja em **um** projeto. Com mais
de um, "tirar do projeto" não tem resposta única.

## Fora de escopo, e por quê

- **Página pública para o workspace inteiro** — é wiki, e resolve outro problema.
  Ver o ADR.
- **Compartilhar página de projeto** — travado de propósito: criaria duas fontes
  de acesso concorrentes para a mesma página.
- **Comentário em página** — não existe hoje nem em projeto.
