# Tarefa recorrente — Matriz de compatibilidade

**Executada em 14/08/2026**, depois da entrega — a funcionalidade foi para
produção na v1.7.0 e redesenhada na v1.8.0 sem esta matriz, o que é dívida de
processo registrada aqui.

Cada linha traz o tratamento e a evidência: `[T]` teste de contrato em
`apps/api/plane/tests/contract/{db,app}/test_recurring_work_items*.py`, `[V]`
validação visual em stack local, `[I]` inspeção de código.

## Ciclo de vida da tarefa

| #   | Recurso existente | Tratamento | Verificação |
| --- | --- | --- | --- |
| 1 | Estados e grupos | A ocorrência nasce na etapa da regra; etapa excluída cai na padrão do projeto | ✓ `[T]` test_copies_the_source_work_item · `[I]` `_estado_inicial` confere exclusão lógica |
| 2 | Botão Concluir (ADR 0009) | Concluir a origem dispara a próxima no modo "após conclusão"; concluir ocorrência idem | ✓ `[T]` test_completing_the_source_starts_the_series |
| 3 | Cancelamento | Libera a guarda, mas **não** dispara a próxima — cancelada não é concluída | ✓ `[I]` `agendar_apos_conclusao` exige grupo `completed` |
| 4 | Reabertura | Volta a contar como trabalho aberto na guarda | ✓ `[I]` `_tem_trabalho_aberto` lê o grupo atual |
| 5 | Arquivamento manual | Arquivar a origem **pausa** a série; desarquivar retoma da próxima data | ✓ `[T]` test_archived_source_pauses_the_rule |
| 6 | Exclusão da origem | Exclui a regra junto; a rede de segurança é o job, porque a exclusão é lógica | ✓ `[T]` test_deleted_source_deletes_the_rule |
| 7 | Exclusão de ocorrência | Não afeta a série, e **não segura a guarda** | ✓ `[T]` test_a_deleted_occurrence_does_not_hold_the_guard |
| 8 | Hard delete diário | FK CASCADE remove regra e ocorrências | ✓ `[I]` `on_delete=CASCADE` em `source_issue` e no registro |

## Automações e trabalho em massa

| #   | Recurso existente | Tratamento | Verificação |
| --- | --- | --- | --- |
| 9 | Automação de arquivar | **Pula origens de recorrência ativa** — máquina não pausa série em silêncio | ✓ `[I]` `_origens_de_recorrencia_ativa` |
| 10 | Automação de fechar | Idem; fechar a origem à revelia travaria o modo "após conclusão" | ✓ `[I]` mesma exclusão |
| 11 | Automação alcança ocorrências antigas | Desejável: é a limpeza do histórico | ✓ `[I]` ocorrência é tarefa comum |
| 12 | Arquivamento em massa | Arquiva a origem e **pausa** a série, como o arquivamento manual — ato humano deliberado, diferente da automação | ✓ `[I]` `BulkArchiveIssuesEndpoint` · ⚠ ver Lacunas |
| 13 | Exclusão em massa | Exclusão lógica; o job apaga a regra na rodada seguinte, e o painel já a esconde | ✓ `[I]` `get_queryset` filtra `source_issue__deleted_at` |

## Estrutura da tarefa

| #   | Recurso existente | Tratamento | Verificação |
| --- | --- | --- | --- |
| 14 | Subtarefas | Copiadas: um nível, abertas, sem data, teto de 50 | ✓ `[T]` test_subtasks_come_along_open_and_dateless |
| 15 | Subtarefa como origem | Bloqueada — a série viraria árvore | ✓ `[T]` test_a_subtask_cannot_become_a_source |
| 16 | Tarefa gerada como origem | Bloqueada; a trava é o rastro | ✓ `[T]` test_a_generated_task_cannot_become_a_source |
| 17 | Ciclo e módulo | A ocorrência **nasce fora dos dois**; adicionada à mão, conta normalmente | ✓ `[I]` a cópia não os inclui · corrigido em doc (ver Achados) |
| 18 | Relações entre tarefas | Não copiadas — descrevem aquela execução | ✓ `[I]` `_criar_ocorrencia` |
| 19 | Tipo de tarefa e estimativa | Copiados da origem | ✓ `[T]` test_copies_the_source_work_item |
| 20 | Épico | `IssueType.is_epic` existe, mas sem caminho de origem nesta edição | ✓ `[I]` |
| 21 | Rascunho | Não pode ser origem | ✓ `[I]` `validate_source_issue` |
| 22 | Anexos | Fora do escopo (custo de storage por ocorrência) | ✓ `[I]` |
| 23 | Duplicar tarefa ("Fazer uma cópia") | Não carrega a recorrência — ela não é campo da tarefa | ✓ `[I]` payload de duplicação |

## Pessoas e permissões

| #   | Recurso existente | Tratamento | Verificação |
| --- | --- | --- | --- |
| 24 | Responsáveis | Copiados; sem nenhum, entra o padrão do projeto | ✓ `[T]` test_the_project_default_assignee_catches_the_orphan |
| 25 | Responsável padrão do projeto | Mesma validação do caminho normal; nunca sobrepõe responsável real | ✓ `[T]` test_the_default_assignee_never_overrides_a_real_one |
| 26 | Remoção de membro | Não é travada; avisa quantas recorrentes e oferece transferência | ✓ `[T]` test_for_member_counts_the_rules · `[V]` modal de remoção |
| 27 | Responsável inativo | Descartado na cópia; alerta no painel com conserto inline | ✓ `[T]` test_an_inactive_assignee_is_dropped_from_the_copy · `[V]` painel |
| 28 | Papéis (admin/membro/convidado) | Escrever é de admin; ler é de todos, porque o selo e o rastro são informação | ✓ `[T]` test_member_cannot_create_but_can_read |
| 29 | Convidado | Lê a lista (o selo depende dela); a página de configurações é de admin | ✓ `[I]` permissão da view + guarda de página |
| 30 | Minhas tarefas | A ocorrência aparece na etapa padrão sem associação — o overlay é aditivo (ADR 0002) | ✓ `[I]` anotação com `Coalesce` em `my_tasks.py` |

## Plataforma

| #   | Recurso existente | Tratamento | Verificação |
| --- | --- | --- | --- |
| 31 | Atividade, webhook e notificação | Toda ocorrência dispara, com o autor da regra como ator | ✓ `[I]` `issue_activity.delay` na geração |
| 32 | Triagem (intake) | A ocorrência não passa: trabalho agendado por admin já está aprovado | ✓ `[I]` criação direta, sem registro de intake |
| 33 | API pública (`plane/api`) | Conclusão externa dispara a próxima — o funil de atividade é o mesmo | ✓ `[I]` `issue_activity.delay` em `api/views/issue.py` |
| 34 | Espaço público (`space`) | Nenhuma rota de recorrência exposta | ✓ `[I]` rotas só em `plane/app` |
| 35 | Mover tarefa entre projetos | Não existe nesta edição; a regra guarda o projeto e a origem no mesmo | ✓ `[I]` sem endpoint de troca de projeto |
| 36 | Multi-workspace | Escopo por workspace em modelo, consultas e rotas | ✓ `[I]` + `[T]` toda a suíte usa slug |
| 37 | Fuso e semana (ADR 0005/0006) | Datas calculadas no fuso do projeto; semana começa no domingo | ✓ `[T]` toda a classe TestAgenda |
| 38 | i18n | Chaves em `recurring_work_items.*`, pt-BR (ADR 0004) | ✓ CI verde em todos os PRs |
| 39 | Exportações e analytics | A ocorrência é tarefa comum; nada de especial a tratar | ✓ `[I]` |
| 40 | Beat / worker | Job a cada 15 minutos; uma regra quebrada não derruba as outras | ✓ `[I]` `try/except` por regra em `generate_recurring_work_items` |

## Achados da execução

**1. Consulta por regra na listagem (corrigido).** A F5 introduziu duas
consultas por regra dentro do serializer — e o selo do quadro pede essa lista a
cada render, então o custo crescia com o número de recorrentes do projeto. Os
dois conjuntos passam a vir prontos do contexto da view. Com 5 regras são **4
consultas**; antes seriam ~14. Fixado em
`test_the_list_does_not_query_per_rule`, com teto apertado de propósito: teto
folgado deixaria a regressão passar sem ninguém notar.

**2. "Conta em ciclo e módulo" (corrigido em documentação).** A frase vinha do
v1 e sobreviveu ao redesenho, que tirou ciclo e módulo da cópia. Lida num
manual, prometia que a ocorrência entra no ciclo. Precisada na especificação, no
manual e com nota no ADR: nasce fora dos dois; adicionada à mão, conta normal.

**3. Etapa pessoal da ocorrência (suspeita descartada).** A ocorrência é criada
direto no banco, sem passar pelo funil que sincroniza a etapa pessoal — parecia
buraco em "Minhas tarefas". Não é: a etapa é anotação com fallback para a
padrão (ADR 0002), então a tarefa sem associação aparece corretamente. O
desenho aditivo já cobria.

## Lacunas conhecidas

Comportamentos corretos, mas que merecem melhoria — anotados, não corrigidos
nesta execução:

- **Arquivar a origem não avisa que pausa a série.** O comportamento é o
  documentado, e arquivar é ato deliberado; ainda assim, um aviso no momento do
  arquivamento seguiria a mesma regra da remoção de membro ("o ato acontece, a
  consequência não é silenciosa").
- **O selo do quadro depende da listagem inteira do projeto.** Hoje é uma
  chamada compartilhada por todos os cartões via SWR, com 4 consultas. Projetos
  com muitas recorrentes podem justificar um endpoint enxuto no futuro.
