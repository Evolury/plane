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

- [ ] F3.1 Integração do agrupamento conforme ADR 0002
- [ ] F3.2 Kanban: colunas = etapas do usuário; drag entre colunas chama
      `move`; reordenação dentro da coluna persiste `sort_order`
- [ ] F3.3 Lista: grupos = etapas; mover via drag e via seletor no card
- [ ] F3.4 Itens sem associação renderizam na etapa padrão; mover cria a
      associação (verificar otimismo/rollback do MobX store)

**Aceite:** mover e reordenar persistem e sobrevivem a reload; nenhum efeito no
work item real (conferir atividade vazia); layouts trocam por display filters.

## F4 — Gestão de etapas

- [ ] F4.1 Painel "Etapas" na página — espelho adaptado de `project-states/`
      (lista por grupo, cores, arrasto para reordenar)
- [ ] F4.2 Criar/editar/excluir com validações (nome único, padrão não
      excluível) e modal de exclusão informando a migração
- [ ] F4.3 Marcar como padrão
- [ ] F4.4 Estados de carregamento e empty states

**Aceite:** paridade de UX com a tela de estados de projeto; excluir etapa com
itens os move para a padrão na UI sem reload.

## F5 — Refinamento

- [ ] F5.1 Bloco `my_tasks` em `ISSUE_DISPLAY_FILTERS_BY_PAGE` (filtros:
      prioridade, projeto, etiqueta, datas; properties; ordenação)
- [ ] F5.2 Peek overview + quick actions integrados
- [ ] F5.3 Empty state da página (sem itens atribuídos) com ilustração padrão

**Aceite:** filtros persistem por página sem vazar para "Seu trabalho";
cenários 15–17 da [compatibilidade.md](compatibilidade.md) passam.

## F6 — Fechamento

- [ ] F6.1 i18n: chaves nos 19 locales via skill `translate`;
      `i18n-sync-check` verde
- [ ] F6.2 Executar a [matriz de compatibilidade](compatibilidade.md) completa,
      marcando cada linha
- [ ] F6.3 Atualizar status em `docs/README.md` e revisar
      especificacao/arquitetura contra o que foi construído
- [ ] F6.4 Entrada no `CHANGELOG.md` (minor — funcionalidade nova)

**Aceite:** checklist da matriz assinado; `pnpm check` + pytest verdes; release
minor cortada conforme [VERSIONING.md](../../../../VERSIONING.md).
