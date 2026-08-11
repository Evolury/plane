# Minhas tarefas — Arquitetura

- **Especificação:** [especificacao.md](especificacao.md) ·
  **ADR:** [0001](../../decisoes/0001-minhas-tarefas-overlay-pessoal.md)
- Caminhos de arquivo são relativos à raiz do repositório.

## Modelo de dados

Duas tabelas novas, aditivas, seguindo o precedente user-scoped de `Sticky`
(`apps/api/plane/db/models/sticky.py`). Nenhuma tabela herdada muda.

```python
class WorkStage(BaseModel):                    # db.WorkStage
    workspace   FK db.Workspace  (CASCADE, related_name="work_stages")
    owner       FK User          (CASCADE, related_name="work_stages")
    name        CharField(255)
    color       CharField(255)
    group       CharField(choices=StateGroup sem TRIAGE)
    sort_order  FloatField(default=65535)
    is_default  BooleanField(default=False)
    # unique: (workspace, owner, name) entre não deletados

class WorkStageIssue(BaseModel):               # db.WorkStageIssue
    workspace   FK db.Workspace  (CASCADE)
    owner       FK User          (CASCADE)
    stage       FK WorkStage     (CASCADE, related_name="stage_issues")
    issue       FK db.Issue      (CASCADE, related_name="work_stage_issues")
    sort_order  FloatField(default=65535)
    # unique: (owner, issue) entre não deletados — um item, uma etapa por usuário
```

Notas:

- `owner` denormalizado em `WorkStageIssue` para consultar sem join em stage.
- `BaseModel` já fornece soft delete (`deleted_at`), auditoria e UUID.
- O grupo `triage` fica fora das choices — mesmo recorte da UI de estados.
- Associação órfã (item desatribuído) é inerte: a listagem parte dos itens
  atribuídos, então ela simplesmente não é lida. Se o item for reatribuído, a
  associação volta a valer (comportamento da spec). Hard delete do item remove
  em cascata.

### Seed

No `GET /stages/`, se o usuário não tem etapa naquele workspace, o seed da
especificação é criado dentro de transação (`get_or_create` guardado por lock
leve) — mesmo padrão do seed de estados em projeto
(`apps/api/plane/db/models/state.py`, `DEFAULT_STATES`).

## API (app interna)

Views em `apps/api/plane/app/views/workspace/my_tasks.py` (novo), URLs em
`apps/api/plane/app/urls/workspace.py` (aditivo). Permissão:
`WorkspaceEntityPermission` com roles admin/membro; **toda consulta filtra
`owner=request.user`** — não existe parâmetro de usuário na rota.

| Método         | Rota                                                        | Ação                                                                  |
| -------------- | ----------------------------------------------------------- | --------------------------------------------------------------------- |
| GET / POST     | `/api/workspaces/<slug>/my-tasks/stages/`                   | Listar (com seed) / criar etapa                                       |
| PATCH / DELETE | `/api/workspaces/<slug>/my-tasks/stages/<pk>/`              | Editar / excluir (migra itens para a padrão; recusa excluir a padrão) |
| POST           | `/api/workspaces/<slug>/my-tasks/stages/<pk>/mark-default/` | Trocar a etapa padrão (transacional, espelho do mark-as-default)      |
| GET            | `/api/workspaces/<slug>/my-tasks/issues/`                   | Work items atribuídos + `stage_id` anotado (null ⇒ etapa padrão)      |
| POST           | `/api/workspaces/<slug>/my-tasks/issues/<issue_id>/move/`   | `{stage_id, sort_order?}` — upsert da associação                      |

A listagem reusa a consulta-base de
`WorkspaceUserProfileIssuesEndpoint` (`apps/api/plane/app/views/workspace/user.py`)
restrita a `assignees__in=[request.user]`, com `stage_id` anotado por subquery
em `WorkStageIssue`. Mesmos recortes: sem arquivados, sem triage, projetos em
que o usuário é membro.

**Silêncio deliberado:** `move` e o CRUD de etapas não passam por
`issue_activity`, webhooks ou notificações ([ADR 0001](../../decisoes/0001-minhas-tarefas-overlay-pessoal.md)).

## Frontend

### Pontos de integração em código herdado (todos aditivos, marcados `Evolury:`)

| Arquivo                                                               | Mudança                                                                    |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `packages/constants/src/workspace.ts`                                 | Item `my-tasks` em `WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS`             |
| `apps/web/core/components/workspace/sidebar/sidebar-menu-items.tsx`   | Composição do item abaixo de `your-work` (preferências enabled/sort_order) |
| `apps/web/core/components/workspace/sidebar/helper.tsx`               | Ícone do item                                                              |
| `apps/web/core/components/navigation/customize-navigation-dialog.tsx` | Entrada `my_tasks`                                                         |
| `apps/web/app/routes/core.ts`                                         | Rota `:workspaceSlug/my-tasks` (layout + page, ao lado de stickies/drafts) |
| `packages/types/src/issues/issue.ts`                                  | `EIssuesStoreType.MY_TASKS` (entrada de enum)                              |
| `packages/constants/src/issue/filter.ts`                              | Bloco `my_tasks` em `ISSUE_DISPLAY_FILTERS_BY_PAGE`                        |
| `apps/web/core/components/power-k/config/navigation/*`                | Comando "Ir para minhas tarefas"                                           |

### Estrutura nova

```
apps/web/app/(all)/[workspaceSlug]/(projects)/my-tasks/
├── layout.tsx · header.tsx · page.tsx

apps/web/core/store/issue/my-tasks/        # espelho de store/issue/profile/
├── issue.store.ts · filter.store.ts · stage.store.ts · index.ts

apps/web/core/components/my-tasks/
├── root.tsx                               # página: layouts + filtros + peek
├── stages/                                # gestão de etapas — espelho adaptado
│   └── (group-list, stage-item, create-update, mark-as-default, delete-modal)
└── roots/                                 # MyTasksListLayout, MyTasksKanbanLayout

apps/web/core/services/my-tasks.service.ts # cliente da API acima
```

A gestão de etapas é cópia adaptada de
`apps/web/core/components/project-states/` (mesma UX, store diferente). Cópia,
e não parametrização do original: mantém o arquivo herdado intocado e a
divergência auditável — mesma razão registrada no commit da marca Evolury.

### O ponto crítico: agrupamento por etapa nos layouts

Todo agrupamento hoje deriva de campo do work item:

- colunas: `getGroupByColumns` em
  `apps/web/core/components/issues/issue-layouts/utils.tsx` (mapa
  `GroupByColumnTypes → getter`);
- chave por item: `base-issues.store.ts` (`getDefaultGroupValue`, mapeamentos
  `state_detail.group → state_id → stateMap.group`);
- drop no kanban: payload de atualização derivado da coluna de destino no
  `base-kanban-root`.

Etapa pessoal exige uma fonte externa (o mapa de associações). Duas abordagens,
a decidir no **spike F0** com código de prova:

- **(a) Fonte de agrupamento aditiva** — novo `GroupByColumnTypes`
  `"my_task_stage"`: getter de colunas lê o stage.store; resolução de chave e
  payload de drop ganham um caso novo. Reusa `BaseKanBanRoot`/`BaseListRoot`
  inteiros; toca 3 arquivos compartilhados de forma aditiva.
- **(b) Store dedicado com resolução própria** — o store `MY_TASKS` sobrescreve
  a derivação de grupos e a página usa roots próprios por cima dos componentes
  de coluna (`KanbanGroup`, blocos de lista). Zero mudança em código
  compartilhado; mais código próprio.

Critério de decisão: (a) vence se os casos novos ficarem contidos e óbvios;
(b) vence se (a) exigir espalhar condicionais. O resultado vira **ADR 0002**.

## Testes

- **pytest (obrigatório, F1):** CRUD de etapas; seed idempotente sob
  concorrência; unicidade da padrão; exclusão migra associações; `move` upsert
  e reorder; listagem anota etapa e respeita recortes (arquivado, triage,
  desatribuído, multi-projeto); isolamento entre usuários e workspaces;
  ausência de atividade/webhook após `move`.
- **Front:** `pnpm check` (tipos/lint/formato) e os cenários manuais da
  [compatibilidade.md](compatibilidade.md).
