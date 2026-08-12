# Terminologia "Tarefa" — Backlog de implementação

Decisão e glossário: [ADR 0003](../../decisoes/0003-terminologia-tarefa-pt-br.md).
Escopo aprovado em 12/08/2026: somente pt-BR; sobras hardcoded na mesma
entrega; "subtarefa" como derivado canônico.

## T0 — Documentação

- [x] ADR 0003 (decisão, escopo e glossário)
- [x] Backlog (este arquivo)

## T1 — Rename no i18n pt-BR (~581 ocorrências, 19 arquivos)

Revisão string a string com concordância de gênero — sem regex cega.
Arquivos por volume: common (151), work-item (92), work-item-type (49),
empty-state (49), workspace (38), project-settings (34), project (30),
inbox (19), tour (16), settings (16), template (15), power-k (15), cycle (9),
workflow (6), integration (6), workspace-settings (4), notification (4),
navigation (3), home (3).

- [ ] T1.1 Lote 1: common, work-item, work-item-type
- [ ] T1.2 Lote 2: empty-state, workspace, project-settings, project
- [ ] T1.3 Lote 3: demais 12 arquivos
- [ ] T1.4 Revisão integral do diff (concordância, duplo espaço, truncamentos)

## T2 — Internacionalizar sobras hardcoded (142 linhas, 71 arquivos web)

Texto em inglês fora do i18n vira chave nova: `en` mantém "work item…",
pt-BR recebe "tarefa…", demais locales via fluxo da skill `translate`.

- [ ] T2.1 Inventário linha a linha (agrupado por área)
- [ ] T2.2 Área atividade (feed/histórico — `core/activity.tsx` e helpers)
- [ ] T2.3 Área ciclos (ciclo ativo, gráficos, transferência)
- [ ] T2.4 Demais áreas (estimativas, upgrades, avulsos)
- [ ] T2.5 `i18n-sync-check` verde (paridade das chaves novas nos 19 locales)

## T3 — Validação e entrega

- [ ] T3.1 `pnpm check` completo
- [ ] T3.2 Visual na stack isolada: criação de tarefa, peek, lista/kanban,
      intake, ciclos, tipos de tarefa, empty states, Minhas tarefas
- [ ] T3.3 Testes de contrato (backend intocado — suítes devem passar sem
      alteração)
- [ ] T3.4 PR(s), CI, merge e deploy em plane.evolury.app.br
- [ ] T3.5 CHANGELOG + release
