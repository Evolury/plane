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

- [x] T1.1 Lote 1: common, work-item, work-item-type
- [x] T1.2 Lote 2: empty-state, workspace, project-settings, project
- [x] T1.3 Lote 3: demais 12 arquivos
- [x] T1.4 Revisão integral do diff — 559 strings; correções manuais de
      concordância (76 sinalizadas + 25 re-varridas) e 9 hipercorreções
      (sujeito masculino antes de "de tarefa": Tipo/Título/Link/ID)

## T2 — Internacionalizar sobras hardcoded (142 linhas, 71 arquivos web)

Texto em inglês fora do i18n vira chave nova: `en` mantém "work item…",
pt-BR recebe "tarefa…", demais locales via fluxo da skill `translate`.

Fora de escopo (inventário 12/08/2026): comentários de código,
`console.*`/`throw`, meta-keywords de SEO e as ~40 strings de marketing de
upsell dos planos pagos do Plane (`billing/comparison/plans.tsx`,
`active-cycles-upgrade`, `bulk-operations/upgrade-banner`) — páginas de
venda do Plane Pro; candidatas a remoção do fork em decisão futura.

- [x] T2.1 Inventário linha a linha (agrupado por área) — ~45 linhas de UI
      visível em ~30 arquivos
- [x] T2.2 Área atividade (feed/histórico — `core/activity.tsx` e helpers)
- [x] T2.3 Área ciclos (ciclo ativo, gráficos, transferência)
- [x] T2.4 Demais áreas (estimativas, upgrades, avulsos)
- [x] T2.5 44 chaves novas presentes nos 19 locales (paridade verificada)

## T3 — Validação e entrega

- [x] T3.1 `pnpm check` completo
- [x] T3.2 Visual na stack isolada — home, Minhas tarefas, peek, lista do
      projeto, modais de criação/exclusão, arquivos e ciclos; varredura
      automática por "item de trabalho" zerada em todas as telas
- [x] T3.3 Backend intocado (nenhum arquivo de apps/api no diff)
- [ ] T3.4 PR(s), CI, merge e deploy em plane.evolury.app.br
- [ ] T3.5 CHANGELOG + release
