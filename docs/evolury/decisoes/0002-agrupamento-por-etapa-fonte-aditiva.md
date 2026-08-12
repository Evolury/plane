# ADR 0002 — Agrupamento por etapa como fonte aditiva nos layouts

- **Status:** Aceito (11/08/2026)
- **Contexto:** funcionalidade [minhas-tarefas](../funcionalidades/minhas-tarefas/arquitetura.md);
  resolve a escolha (a)/(b) deixada em aberto pelo [ADR 0001](0001-minhas-tarefas-overlay-pessoal.md)
- **Origem:** spike F0 do [backlog](../funcionalidades/minhas-tarefas/backlog.md)

## Contexto

Os layouts lista/kanban precisam agrupar por etapa pessoal. O ADR 0001 deixou
duas abordagens em aberto: **(a)** registrar a etapa como fonte de agrupamento
nova no código compartilhado, ou **(b)** store dedicado com resolução própria e
roots reimplementados. O spike F0 rastreou o pipeline de ponta a ponta e rodou
uma sonda de compilação para medir o custo real de (a).

## O que o rastreio revelou

O pipeline inteiro é **genérico sobre uma chave de campo do work item** — não
há nada intrinsecamente "de estado" ou "de prioridade" nele:

1. **Servidor** — o endpoint recebe `group_by` como nome de campo, agrupa e
   pagina por grupo (`GroupedOffsetPaginator` aceita qualquer
   `group_by_field_name`, inclusive campo anotado; `apps/api/plane/utils/paginator.py:195`).
2. **Parâmetro** — o front traduz a opção de exibição para o campo do servidor
   via enum `EIssueGroupByToServerOptions`
   (`packages/constants/src/issue/common.ts:27`).
3. **Store** — o agrupamento local resolve a chave por
   `ISSUE_GROUP_BY_KEY`/`ISSUE_FILTER_DEFAULT_DATA`, ambos `Record<..., keyof TIssue>`
   (`apps/web/core/store/issue/helpers/base-issues.store.ts:115,129`).
4. **Colunas** — `getGroupByColumns` é um mapa tipo→getter
   (`apps/web/core/components/issues/issue-layouts/utils.tsx:142`).
5. **Drop** — `handleGroupDragDrop` constrói o payload como
   `{ [ISSUE_FILTER_DEFAULT_DATA[groupBy]]: destino.groupId }` e delega ao
   `updateIssue` do store ativo (`utils.tsx:539`).

**Consequência:** se o nosso endpoint anotar a etapa como campo do payload
(`my_task_stage_id`, via subquery em `WorkStageIssue` com `Coalesce` para a
etapa padrão), a etapa se comporta como qualquer campo agrupável — paginação por
grupo, reagrupamento otimista e drag-drop funcionam sem reimplementação.

A **sonda de compilação** (membros `"my_task_stage"` nas uniões
`TIssueGroupByOptions` e `GroupByColumnTypes` + campo opcional em `TBaseIssue`)
provou que os pontos exaustivos são exatamente **quatro**, todos guardados pelo
compilador:

| Ponto                                                           | Entrada nova                           |
| --------------------------------------------------------------- | -------------------------------------- |
| `groupByColumnMap` (`issue-layouts/utils.tsx:142`)              | getter lendo o stage.store             |
| `ISSUE_GROUP_BY_KEY` (`base-issues.store.ts:115`)               | `"my_task_stage": "my_task_stage_id"`  |
| `ISSUE_FILTER_DEFAULT_DATA` (`base-issues.store.ts:129`)        | `"my_task_stage": "my_task_stage_id"`  |
| `EIssueGroupByToServerOptions` (`constants/issue/common.ts:27`) | `"my_task_stage" = "my_task_stage_id"` |

Nenhum outro arquivo falhou o typecheck do `web` com a sonda aplicada.

## Decisão

**Abordagem (a) — fonte de agrupamento aditiva**, na variante híbrida:

1. As uniões `TIssueGroupByOptions`/`GroupByColumnTypes` ganham
   `"my_task_stage"`, `TBaseIssue` ganha `my_task_stage_id?: string | null`, e
   os quatro pontos acima ganham uma entrada cada — tudo aditivo e marcado
   `Evolury:`.
2. O endpoint `GET /my-tasks/issues/` anota `my_task_stage_id` com `Coalesce`
   para a etapa padrão do usuário — todo item chega com etapa concreta e o
   agrupamento server-side pagina por ela.
3. O store `MY_TASKS` (espelho do `ProfileIssues`) sobrescreve `updateIssue`:
   payload contendo `my_task_stage_id` roteia para
   `issueUpdate(..., shouldSync=false)` (atualização local otimista +
   reagrupamento, já com rollback) seguido do `POST .../move/` do nosso
   service, com reversão manual em caso de falha; qualquer outro payload segue
   o fluxo padrão (`issueUpdate` → PATCH do issue).
4. A página restringe `group_by` a `my_task_stage` (spec: agrupamento fixo), de
   modo que a fonte nova não aparece nas demais páginas — o valor novo só é
   usado onde o bloco `my_tasks` de `ISSUE_DISPLAY_FILTERS_BY_PAGE` o oferece.

## Alternativa descartada

**(b) Store dedicado com resolução própria** exigiria reimplementar, em código
próprio, a paginação por grupo, o reagrupamento otimista com rollback e o
payload de drop — centenas de linhas paralelas de manutenção permanente para
evitar seis edições aditivas de uma linha guardadas pelo compilador. O critério
do ADR 0001 ("(a) vence se os casos novos ficarem contidos e óbvios") foi
atendido com folga.

## Consequências

- F3 reusa `BaseKanBanRoot`/`BaseListRoot` e o drag-drop existentes por inteiro.
- Os quatro pontos compartilhados tocados são exaustivos por tipo: qualquer
  refactor futuro que os altere quebra o build em vez de quebrar a página.
- O campo `my_task_stage_id` só é anotado pelo nosso endpoint; nos demais
  fluxos ele é `undefined` — por isso é opcional no tipo e inerte fora da
  página.
- `POST .../move/` permanece fora de `issue_activity`/webhooks (ADR 0001); o
  PATCH normal de issue nunca recebe `my_task_stage_id` porque o roteamento no
  store o intercepta antes.
