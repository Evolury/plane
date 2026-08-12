# Minhas tarefas — Backlog de implementação

Fases sequenciais; cada fase fecha com seus critérios de aceite verdes antes da
seguinte. Branches `feat/minhas-tarefas-<fase>`, PRs para `main` referenciando
os itens daqui (ex.: "Implementa F1.2–F1.4").

## F0 — Spike: agrupamento por etapa nos layouts

Decide a única incerteza técnica do projeto ([arquitetura.md](arquitetura.md),
"O ponto crítico"). Timebox: 1 dia; código descartável.

- [x] F0.1 Abordagem (a) provada por rastreio de ponta a ponta + sonda de
      compilação: uniões estendidas e typecheck do `web` enumerando os pontos
      exaustivos (exatamente 4, todos aditivos)
- [x] F0.2 Abordagem (b) avaliada por custo sobre o mesmo rastreio:
      reimplementaria paginação por grupo, reagrupamento otimista e drop —
      descartada sem protótipo, diferença conclusiva
- [x] F0.3 **[ADR 0002](../../decisoes/0002-agrupamento-por-etapa-fonte-aditiva.md)**
      escrito e aceito

**Aceite:** ✓ ADR 0002 aceito em 11/08/2026; F3 usará a fonte aditiva
`my_task_stage` com campo anotado `my_task_stage_id`.

## F1 — Backend

- [x] F1.1 Modelos `WorkStage` e `WorkStageIssue` + migration `0125_evolury_work_stages`
      (validada com `makemigrations --check`)
- [x] F1.2 Seed idempotente das 5 etapas padrão no primeiro `GET /stages/` (e
      na listagem de issues), com corrida absorvida pela constraint de nome
- [x] F1.3 CRUD de etapas + `mark-default` transacional + exclusão com migração
      de associações para a padrão
- [x] F1.4 `GET /my-tasks/issues/` — consulta-base do perfil restrita a
      atribuídos, `my_task_stage_id` anotado com Coalesce para a padrão e
      paginação agrupada (paginator construído no endpoint; a
      ISSUE_GROUP_BY_ALLOWLIST fica intacta de propósito)
- [x] F1.5 `POST /issues/<id>/move/` — upsert de associação + `sort_order`
- [x] F1.6 Suíte pytest: 27 testes de contrato

**Aceite:** ✓ 11/08/2026 — suíte completa da API verde na stack
`docker-compose-test.yml` (543 testes, 27 novos); toda rota filtra
`owner=request.user`; `move` não gera atividade nem toca o estado real (testes
explícitos).

## F2 — Fundação frontend

- [x] F2.1 Rota `my-tasks` (layout/header/page) registrada em `routes/core.ts`
- [x] F2.2 Item de sidebar abaixo de "Seu trabalho" (chave `my_tasks` nas
      preferências do servidor, ancorada no sort_order do your_work para
      usuários existentes) + ícone + "Personalizar navegação" + Power-K (`gt`)
- [x] F2.3 `my-tasks.service.ts` (7 métodos, cobre também o CRUD da F4) +
      `MyTasksStore` (etapas + listagem + move otimista) +
      `EIssuesStoreType.MY_TASKS`. Nota: na F2 o store é próprio e enxuto —
      o espelho completo do ProfileIssues (issue/filter stores sobre
      BaseIssuesStore) é entregue na F3 junto da integração do ADR 0002,
      quando os layouts base passam a exigi-lo
- [x] F2.4 Página abre com os itens atribuídos agrupados por etapa (seções
      client-side por `my_task_stage_id`, sem drag), com i18n nos 19 locales

**Aceite:** ✓ 11/08/2026 — navegação completa; `pnpm check` 60/60 verde; suíte
da API 543 verdes (preferências com a chave nova incluídas).

## F3 — Layouts com etapas

- [x] F3.1 Integração conforme ADR 0002: uniões + campo `my_task_stage_id` em
      `TBaseIssue` + entradas nos pontos exaustivos. A sonda da F0 achou 4; a
      implementação revelou mais 2 que só aparecem com o enum estendido —
      `EServerGroupByToFilterOptions` (mapa reverso) e a cópia do
      `ISSUE_FILTER_DEFAULT_DATA` no `apps/space` — e `TIssueParams` ganhou
      `my_task_stage` para a paginação por grupo (com o filtro correspondente
      no endpoint)
- [x] F3.2 Kanban sobre `BaseKanBanRoot`: colunas = etapas (getter lê o
      stage store); drag entre colunas roteia para `move`; reordenação dentro
      da coluna persiste o sort pessoal — o payload da página tem `sort_order`
      SOBRESCRITO pelo da associação no servidor, então o cálculo de vizinhos
      do drop opera em base pessoal e o sort real do item nunca é tocado
- [x] F3.3 Lista sobre `BaseListRoot`, mesmos grupos e drag
- [x] F3.4 Sem associação ⇒ etapa padrão (anotação do servidor); mover usa
      `issueUpdate(shouldSync=false)` otimista com reversão manual em falha.
      Roteamento no `updateIssue` do store: `my_task_stage_id` e/ou
      `sort_order` sozinho vão para o `move/`; qualquer outra edição segue o
      PATCH normal com atividade
- [x] extra: alternador lista/kanban no header (aceite "layouts trocam por
      display filters"); a linha completa de filtros fica na F5

**Aceite:** ✓ 11/08/2026 — persistência de mover/reordenar coberta por
contrato (544 testes verdes, incl. o de sort_order pessoal no payload e os de
silêncio do ADR 0001); `pnpm check` 60/60. **Validação visual executada** em
stack local (login → sidebar → lista → kanban → drag → reload): drag persiste,
estado real e sort_order reais intocados, 0 atividades no banco. A validação
encontrou e corrigiu dois bloqueios que os tipos não pegam: etapas vazias
ocultas no kanban (show_empty_groups virou estrutural da página — sem coluna
vazia não há destino de drag) e a DRAG_ALLOWED_GROUPS, allowlist de
agrupamentos arrastáveis que não estava no rastreio da F0 (7º ponto).

## F4 — Gestão de etapas

- [x] F4.1 Painel "Etapas" na página (modal via botão no header). Melhor que o
      previsto: em vez de cópia adaptada, a família `project-states/` é
      REUSADA — o `GroupList` é parametrizado por callbacks e só lê campos
      comuns, então um adaptador `TWorkStage↔IState`
      (sequence↔sort_order, default↔is_default) bastou; zero cópia das ~1100
      linhas e paridade de UX por construção
- [x] F4.2 Criar/editar/excluir pela UI reusada; validações do backend F1
      (nome único 400, padrão não excluível 400 — o componente já trata) e o
      modal de exclusão herdado
- [x] F4.3 Marcar como padrão (mark-default transacional da F1); excluir ou
      trocar a padrão refaz a listagem sem reload
- [x] F4.4 Loading/empty herdados do GroupList; painel com scroll interno

**Aceite:** ✓ 12/08/2026 — paridade por reuso; validação visual em stack
planedev: painel renderiza os 5 grupos com as etapas, criação de "Delegadas"
confirmada na UI (toast) e no banco, opções de hover presentes, página ao fundo
reagrupada em tempo real. Nit registrado para F5/F6: toasts herdados dizem
"estado" onde a página diz "etapa" (chaves da família reusada).

## F5 — Refinamento

- [x] F5.1 UI completa de filtros: linha de filtros ricos
      (`WorkspaceLevelWorkItemFiltersHOC` + `WorkItemFiltersRow`, entidade
      MY_TASKS), toggle no header, dropdown "Exibir" (propriedades/ordenação)
      e `LayoutSelection` padrão substituindo o toggle artesanal da F3. O
      bloco `my_tasks` já existia da F3; entrou a opção de agrupamento
      rotulada ("Etapa", 8º ponto compartilhado aditivo). Validado no
      navegador: filtro Prioridade=Urgente reduz a 1 item com grupos
      preservados
- [x] F5.2 Peek overview + quick actions já integrados desde a F3 (reuso dos
      roots base); re-verificados na validação visual
- [x] F5.3 Empty state ilustrado (asset work-item) com títulos nos 19 locales,
      e empty state de busca (com "Limpar") quando filtros ativos zeram a
      lista. A validação achou e corrigiu um bug de contrato: com zero
      resultados o GroupedOffsetPaginator devolve `results: {}` sem as chaves
      dos grupos e o front nunca sai do "carregando" — o endpoint agora
      garante toda etapa presente na resposta agrupada (teste de contrato)

**Aceite:** ✓ 12/08/2026 — filtros persistem por página (localStorage chaveado
por MY_TASKS+workspace, sem vazar para o perfil); suíte da API 545 verdes (29
de minhas-tarefas); `pnpm check` 60/60; validação visual completa (filtros,
Exibir, empty states com usuário sem atribuições).

## F6 — Fechamento

- [x] F6.1 i18n: chaves da feature nos 19 locales desde as fases (sync verde
      em todos os PRs). Nits resolvidos: valores de prioridade e grupo de
      estado do rich-filters traduzidos (via `getOptionLabel` opcional nos
      configs — beneficia todas as páginas) e toasts da família reusada
      neutralizados em pt-BR ("Criado com sucesso." serve a estados e etapas
      sem parametrizar 6 componentes)
- [x] F6.2 [Matriz de compatibilidade](compatibilidade.md) executada e
      assinada: 23/23 com evidência (teste de contrato, validação visual ou
      inspeção); 2 testes adicionados na execução (hard delete em cascata,
      memória da etapa na reatribuição) — suíte de minhas-tarefas em 31
- [x] F6.3 Arquitetura atualizada com a lista as-built dos pontos de
      integração; status no índice
- [x] F6.4 Entrada v1.1.0 no `CHANGELOG.md` (no PR de release)

**Aceite:** ✓ 12/08/2026 — matriz assinada; `pnpm check` + pytest verdes;
release v1.1.0 cortada pelo fluxo `release/` do VERSIONING.md (primeiro
exercício do `check-version`).

## F7 — Etapa pela janela do work item (pós-v1.1.0)

Espelho do recurso do Asana (spec, "Etapa pela janela do work item").
Decisões de escopo com o produto em 12/08/2026: todas as janelas do work item;
seletor só para responsáveis.

- [x] F7.1 `GET /my-tasks/issues/<id>/stage/` — etapa efetiva (associação ou
      padrão; 404 se não responsável), com seed garantido; 4 testes de
      contrato (suíte my-tasks em 35)
- [x] F7.2 `MyTasksStageSelect` autocontido + prop `workItemId` opcional no
      `MemberDropdown` (threading types→base→options; chip na linha "Você"
      com preventDefault/stopPropagation para não alternar a atribuição)
- [x] F7.3 Prop nos 6 call sites de responsáveis: peek, detalhe, propriedades
      inline (lista/kanban), planilha, intake e relações
- [x] F7.4 i18n nos 19 locales; validação visual em planedev: chip
      "Recém-atribuídas" → seleção "Hoje" → chip atualizado E a página de
      minhas tarefas ao fundo reagrupada em tempo real; atividade vazia

**Aceite:** ✓ 12/08/2026 — validado de ponta a ponta no navegador.
