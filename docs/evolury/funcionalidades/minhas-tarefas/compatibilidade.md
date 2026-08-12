# Minhas tarefas — Matriz de compatibilidade

**Executada em 12/08/2026 (F6).** Cada linha traz o tratamento e a evidência da
verificação: `[T]` teste de contrato em
`apps/api/plane/tests/contract/api/test_my_tasks.py`, `[V]` validação visual em
stack local (screenshots na sessão de desenvolvimento), `[I]` inspeção de
código/design.

| #   | Recurso existente          | Tratamento                                                       | Verificação                                                                          |
| --- | -------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 1   | Múltiplos responsáveis     | Associação por usuário; um não afeta o outro                     | ✓ `[T]` test_annotation_is_per_user                                                  |
| 2   | Estados do projeto         | Overlay (ADR 0001): mover etapa nunca altera estado              | ✓ `[T]` test_move_does_not_touch_issue_state · `[V]` card mantém "Backlog" após drag |
| 3   | Atividade do work item     | `move` fora do `issue_activity`                                  | ✓ `[T]` test_move_creates_no_issue_activity                                          |
| 4   | Webhooks                   | Sem atividade não há gatilho; o módulo não importa o fluxo       | ✓ `[I]` + linha 3                                                                    |
| 5   | Notificações               | Idem — fora do fluxo                                             | ✓ `[I]` + linha 3                                                                    |
| 6   | Automação de arquivamento  | `issue_objects` exclui arquivados; associação inerte             | ✓ `[T]` test_lists_only_assigned_issues (arquivado excluído)                         |
| 7   | Automação de fechamento    | Estado muda; etapa preservada (associação não referencia estado) | ✓ `[I]` modelo + linha 2                                                             |
| 8   | Hard delete diário         | FK CASCADE remove associações                                    | ✓ `[T]` test_hard_delete_cascades_association                                        |
| 9   | Desatribuição/reatribuição | Some da listagem; volta à mesma etapa                            | ✓ `[T]` test_reassignment_restores_previous_stage                                    |
| 10  | Intake / triage            | Recortes espelho do endpoint de perfil                           | ✓ `[I]` consulta idêntica + manager exclui triage                                    |
| 11  | Rascunhos                  | Fora da consulta                                                 | ✓ `[T]` test_lists_only_assigned_issues                                              |
| 12  | Permissões de projeto      | Listagem restrita a projetos em que é membro                     | ✓ `[T]` test_removed_project_member_issues_disappear                                 |
| 13  | Guest                      | 403 em toda a API; item de sidebar restrito                      | ✓ `[T]` test_guest_cannot_access                                                     |
| 14  | Multi-workspace            | Escopo por workspace em modelo, constraints e consultas          | ✓ `[I]` + `[T]` test_seed_is_per_user (isolamento por dono)                          |
| 15  | Peek overview              | Reúso direto; edições reais seguem fluxo padrão                  | ✓ `[V]` F3/F5                                                                        |
| 16  | Quick actions              | Reúso das ações da página de perfil                              | ✓ `[V]` F3                                                                           |
| 17  | Filtros por página         | localStorage chaveado por MY_TASKS+workspace                     | ✓ `[V]` F5 (sem vazamento para o perfil)                                             |
| 18  | Personalizar navegação     | Entrada `my_tasks` como as demais                                | ✓ `[I]` espelho de your_work · `[V]` sidebar F2                                      |
| 19  | Power-K                    | Comando "Ir para minhas tarefas" (`gt`)                          | ✓ `[I]` registro espelho de nav_your_work                                            |
| 20  | i18n (19 locales)          | Chaves via fluxo da skill `translate`                            | ✓ `i18n-sync-check` verde no CI de todos os PRs                                      |
| 21  | API pública / space        | Nenhuma rota exposta                                             | ✓ `[I]` urls só em `plane/app`                                                       |
| 22  | Exclusão de etapa          | Migração transacional para a padrão                              | ✓ `[T]` test_destroy_migrates_associations_to_default · `[V]` F4                     |
| 23  | Seed concorrente           | Idempotente; corrida absorvida por constraint                    | ✓ `[T]` test_seed_race_is_absorbed                                                   |

## Achados das validações (corrigidos durante as fases)

Três defeitos que só a execução da matriz/validação visual expôs — todos
corrigidos e cobertos:

1. **Etapas vazias ocultas no kanban** (F3): `show_empty_groups` caía para
   `false` com filtros persistidos; sem coluna vazia não há destino de drag.
   Visibilidade virou estrutural da página.
2. **`DRAG_ALLOWED_GROUPS`** (F3): allowlist de agrupamentos arrastáveis fora
   do rastreio da F0; sem a entrada, o drop era rejeitado.
3. **Resposta agrupada vazia sem chaves** (F5): `GroupedOffsetPaginator`
   devolve `{}` com zero resultados e o front nunca sai do "carregando"; o
   endpoint garante toda etapa presente
   (`test_grouped_response_always_carries_all_stage_keys`).
