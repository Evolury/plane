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

- [ ] F1.1 Modelos `WorkStage` e `WorkStageIssue` + migrations (comentário
      `Evolury:`, numeração após a última do upstream)
- [ ] F1.2 Seed idempotente das 5 etapas padrão no primeiro `GET /stages/`
- [ ] F1.3 CRUD de etapas + `mark-default` transacional + exclusão com migração
      de associações
- [ ] F1.4 `GET /my-tasks/issues/` — consulta-base do perfil restrita a
      atribuídos, `stage_id` anotado
- [ ] F1.5 `POST /issues/<id>/move/` — upsert de associação + `sort_order`
- [ ] F1.6 Suíte pytest completa (lista em [arquitetura.md](arquitetura.md),
      "Testes")

**Aceite:** suíte verde na stack `docker-compose-test.yml`; nenhuma rota aceita
operar sobre outro usuário; `move` não gera atividade/webhook (teste explícito).

## F2 — Fundação frontend

- [ ] F2.1 Rota `my-tasks` (layout/header/page) registrada em `routes/core.ts`
- [ ] F2.2 Item de sidebar abaixo de "Seu trabalho" + ícone + entrada no
      "Personalizar navegação" + comando Power-K
- [ ] F2.3 `my-tasks.service.ts` + stores (`stage.store`, `issue.store`,
      `filter.store`) + `EIssuesStoreType.MY_TASKS`
- [ ] F2.4 Página abre com os itens atribuídos listados na etapa padrão
      (agrupamento simples, sem drag ainda)

**Aceite:** navegação completa (sidebar, diálogo, Power-K); listagem correta
para usuário com itens em múltiplos projetos; `pnpm check` verde.

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
