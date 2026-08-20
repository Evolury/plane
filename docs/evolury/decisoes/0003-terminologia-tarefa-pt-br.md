# ADR 0003 — "Tarefa" como termo pt-BR para work item

- **Status:** Aceito (12/08/2026)
- **Contexto:** funcionalidade [terminologia-tarefa](../funcionalidades/terminologia-tarefa/backlog.md)

## Contexto

O Plane chama a unidade de trabalho de **work item** ("item de trabalho" no
pt-BR). Para o produto Evolury, o termo adequado é **tarefa** — mais curto,
natural em português e convergente com a página "Minhas tarefas" (que passa a
listar, literalmente, tarefas).

A pergunta estrutural era: isso é tradução ou arquitetura? A varredura
(12/08/2026) respondeu:

- **581 ocorrências** de "item(ns) de trabalho" nos 19 arquivos do locale
  pt-BR (`packages/i18n`), compartilhado por web, space e admin.
- **142 linhas de inglês hardcoded** fora do i18n em **71 arquivos** do web
  (feed de atividade, ciclo ativo, estimativas, gráficos) — débito do
  upstream: essas telas já exibem "work item" em inglês hoje.
- Nenhuma ocorrência visível em e-mails; exportações CSV e mensagens da API
  pública são contrato técnico em inglês.

## Decisão

1. **Camada de tradução, não de estrutura.** Mudam apenas os **valores**
   pt-BR. Chaves de i18n (`work_item_*`), código (`issue`), banco, API,
   webhooks, rotas e exportações permanecem intactos. Zero migração.
2. **Escopo de idioma: somente pt-BR.** Os demais 18 locales mantêm o termo
   nativo deles para work item.
3. **Sobras hardcoded entram na mesma entrega**: as 142 linhas em inglês
   viram chaves de i18n — o `en` mantém "work item"; o pt-BR recebe
   "tarefa". Melhoria colateral para todos os idiomas.
4. **Gênero gramatical é revisão, não regex.** "Item" (masculino) → "tarefa"
   (feminino) flexiona artigos, pronomes e particípios ("novo item criado" →
   "nova tarefa criada"; "ao item" → "à tarefa"; "nenhum item encontrado" →
   "nenhuma tarefa encontrada"). Cada string é revisada individualmente.

## Glossário canônico

| Conceito (en)             | pt-BR anterior               | pt-BR canônico       |
| ------------------------- | ---------------------------- | -------------------- |
| work item                 | item de trabalho             | tarefa               |
| work items                | itens de trabalho            | tarefas              |
| sub-work item             | sub-item de trabalho         | subtarefa            |
| work item type(s)         | tipo(s) de item de trabalho  | tipo(s) de tarefa    |
| recurring work item       | item de trabalho recorrente  | tarefa recorrente    |
| draft work item           | rascunho de item de trabalho | rascunho de tarefa   |
| Epic                      | Épico                        | Épico (inalterado)   |
| My tasks (funcionalidade) | Minhas tarefas               | Minhas tarefas       |
| to-do list (bloco editor) | Lista de tarefas             | Lista de tarefas (¹) |
| Intake (funcionalidade)   | Intake / Entrada             | Triagem (²)          |

(¹) O bloco de checklist do editor coexiste sem conflito prático; manter.

(²) Ver o adendo de 20/08/2026 abaixo.

## Adendo (20/08/2026) — "Intake" vira "Triagem"

O recurso que recebe solicitações de fora chamava-se **Intake** na tela. Pior:
não se chamava só isso. A varredura achou **quatro** termos para a mesma coisa
no pt-BR — "Intake", "Entrada", "entrada" e "recebimento" —, às vezes na mesma
tela de configuração.

Passa a ser **Triagem**, em 40 strings. Palavra portuguesa, descreve o que a
tela faz (avaliar antes de aceitar) e não pede glossário.

**Gênero mudou**, e por isso não foi busca-e-troca: "o Intake" é masculino,
"a Triagem" é feminino. Cada string foi reescrita — "Ativar o Intake" → "Ativar
a Triagem", "O Intake não está habilitado" → "A Triagem não está habilitada",
"tarefas do Intake" → "tarefas da Triagem". É a mesma regra do item 4 acima.

**Não colide com o estado `triage`**, e isso foi conferido: o estado de triagem
é filtrado de toda listagem por `is_triage=False` — some da tela de Estados, do
agrupamento e dos seletores. Ele existe só para segurar o item enquanto ele
espera avaliação. O nome do recurso e o do estado apontarem para a mesma ideia é
coerência, não ambiguidade.

**Não colide com "Caixa de entrada"**, que é o centro de notificações. Antes
colidia: com o Intake às vezes chamado de "Entrada", os dois recursos disputavam
a mesma palavra.

Camada de tradução apenas: chaves (`inbox_issue.*`, `sidebar.intake`), código,
rotas e API seguem com `intake`/`inbox`. O `en` mantém "Intake".

| Conceito (en)           | pt-BR anterior                           | pt-BR canônico                |
| ----------------------- | ---------------------------------------- | ----------------------------- |
| Intake (funcionalidade) | Intake · Entrada · entrada · recebimento | **Triagem**                   |
| Inbox (notificações)    | Caixa de entrada                         | Caixa de entrada (inalterado) |

## Adendo (12/08/2026) — nomes de estado são dado, não rótulo

O grupo de estado `backlog` não tinha tradução no pt-BR e passou a **"Em
espera"** (rótulo, mesma camada desta decisão). A varredura mostrou que
"Backlog" aparecia em dois lugares de naturezas diferentes:

- **rótulo do grupo** (`workspace_projects.state.backlog` e irmãs) —
  tradução, resolvida como o resto deste ADR;
- **nome do estado gravado por projeto** (`DEFAULT_STATES`) — dado. O Plane
  cria "Backlog / Todo / In Progress / Done / Cancelled" em inglês.

Como o produto é pt-BR, os nomes padrão passaram a **"Em espera / A fazer /
Em andamento / Concluído / Cancelado"** (e "Triagem"), e a migração `0127`
renomeia os projetos existentes — **apenas** os que ainda estavam com o nome
padrão em inglês, casando nome + grupo; quem personalizou não é tocado, e
projeto que já tenha o nome de destino fica de fora por causa da constraint
`(name, project)`.

Isso é a única exceção à regra "zero migração" acima, e é deliberada: nome de
estado é conteúdo do projeto, não string de interface — não há como traduzi-lo
pela camada de i18n.

## Consequências

- A UI pt-BR inteira (web, space, admin) fala "tarefa"; textos de outros
  idiomas não mudam.
- Novas strings pt-BR devem seguir o glossário acima (vale para o fluxo da
  skill `translate`).
- O nome do conceito no código continua `issue`/`work item` — comentários e
  documentos técnicos podem usar os dois, mas texto de usuário só "tarefa".
- As telas hoje em inglês passam a ser traduzíveis (chaves novas), reduzindo
  o débito herdado do upstream.
