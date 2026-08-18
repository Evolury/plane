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

## Movimentação diária pelo vencimento (ADR 0014)

Matriz a executar como checklist antes de considerar a F8 entregue. Legenda
igual à do resto do documento: `[T]` provado por teste, `[V]` verificado na
tela, `[I]` inspecionado no código.

| #   | Situação                                  | Esperado                                                   | Prova         |
| --- | ----------------------------------------- | ---------------------------------------------------------- | ------------- |
| 1   | Vencimento ontem                          | Vai para a etapa de vencidas                               | `[T]` · `[V]` |
| 2   | Vencimento hoje                           | Vai para a etapa de hoje                                   | `[T]` · `[V]` |
| 3   | Vencimento amanhã                         | Vai para a etapa de amanhã                                 | `[T]` · `[V]` |
| 4   | Vencimento em D+2                         | Vai para a etapa de depois — **o limite, não D+3**         | `[T]` · `[V]` |
| 5   | Sem vencimento                            | Vai para hoje **e continua sem data**                      | `[T]` · `[V]` |
| 6   | Tarefa concluída e vencida                | Não se move: trava do motor                                | `[T]`         |
| 7   | Tarefa cancelada e vencida                | Não se move: trava do motor                                | `[T]`         |
| 8   | Tarefa em etapa sem automação             | Não sai, mesmo mudando de balde                            | `[T]` · `[V]` |
| 9   | Etapa sem automação como destino          | **Recebe normalmente** — o opt-out é de saída              | `[T]` · `[V]` |
| 10  | Balde sem etapa marcada                   | Tarefa fica onde está                                      | `[T]`         |
| 11  | Uma etapa marcada para dois baldes        | Recebe os dois                                             | `[T]`         |
| 12  | Duas etapas para o mesmo balde            | Recusado pela constraint                                   | `[T]` · `[V]` |
| 13  | Varredura rodando duas vezes no mesmo dia | Nada muda na segunda                                       | `[T]` · `[V]` |
| 14  | Worker fora do ar na virada               | Varredura seguinte se recupera pelo marcador               | `[T]`         |
| 15  | Duas pessoas em fusos diferentes          | Cada uma vira no seu relógio                               | `[I]`         |
| 16  | Arrasto manual para a etapa de hoje       | Vencimento vira hoje                                       | `[T]`         |
| 17  | Arrasto manual para a etapa de amanhã     | Vencimento vira amanhã                                     | `[T]`         |
| 18  | Arrasto manual para depois ou vencidas    | Data **não** é tocada                                      | `[T]`         |
| 19  | Arrasto que muda a data                   | Gera histórico e aciona regras, como edição na tela        | `[I]`         |
| 20  | Tarefa vencida repactuada para o futuro   | Sai de vencidas na varredura seguinte, salvo etapa travada | `[T]` · `[V]` |
| 21  | Etapa marcada sendo excluída              | A marcação some com ela; o balde fica sem etapa            | `[I]`         |
| 22  | Conta nova                                | Nasce com as oito etapas e as marcações do seed            | `[V]`         |

### Executada em 18/08/2026

Verificação da virada feita contra a produção, rodando **a tarefa do beat**, e
não a função interna — o caminho que roda de verdade.

Com o relógio um dia à frente, tudo andou um balde: a que vencia hoje virou
vencida, a de amanhã virou de hoje, a de D+2 virou de amanhã. A sem data
continuou em "hoje" **e sem data**.

Rodar duas vezes no mesmo dia varreu **zero** pessoas e não mudou nada — o
marcador cumprindo o papel.

Uma consequência do seed que vale saber: como Recentes nasce travada, **tarefa
nova não é ordenada pela varredura até alguém a tirar de lá**. É o desenho
pedido — Recentes existe para se tomar conhecimento do que chegou —, e significa
que a varredura administra o que já foi triado, não a caixa de entrada.

As linhas 15, 19 e 21 ficam como `[I]`: dependem de dois fusos simultâneos, do
histórico de uma escrita e da exclusão de etapa, e as três já têm o
comportamento provado por teste noutro lugar da suíte.
