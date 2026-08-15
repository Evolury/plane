# Propriedades personalizadas — matriz de compatibilidade

Executada em 15/08/2026, contra o código em `main`. Mesmo método da F6 da
recorrência: cada linha é uma interação com um recurso existente, e cada
verificação diz **como** foi comprovada — `[T]` teste automatizado, `[V]`
validação visual em stack local, `[I]` inspeção de código.

Decisão: [ADR 0011](../../decisoes/0011-propriedades-personalizadas.md).

## Estrutura da tarefa

| #   | Recurso existente            | Tratamento                                                             | Verificação                                                |
| --- | ---------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- |
| 1   | Criar tarefa                 | Aceita `property_values`; obrigatória barra a criação e só ela         | ✓ `[T]` test_a_required_property_blocks_creation           |
| 2   | Editar tarefa                | Valor tem endpoint próprio; obrigatória não barra edição nem conclusão | ✓ `[T]` test_a_required_property_never_blocks_completion   |
| 3   | Tarefa que já existia        | Obrigatória não a alcança — vale para o que nasce depois               | ✓ `[T]` test_a_required_property_never_blocks_an_existing… |
| 4   | Subtarefa                    | Mesmas propriedades: elas são do projeto, não do nível                 | ✓ `[T]` test_custom_property_values_come_along             |
| 5   | Excluir tarefa               | Valores vão junto pela cascata; contagem ignora tarefa excluída        | ✓ `[T]` test_a_deleted_work_item_does_not_count            |
| 6   | Rascunho                     | Sem interação: o modal de rascunho usa o mesmo formulário              | ✓ `[I]`                                                    |
| 7   | Tipo de tarefa (`IssueType`) | Independentes de propósito — não amarramos as duas decisões            | ✓ `[I]` ADR 0011, alternativas                             |

## Layouts e leitura

| #   | Recurso existente  | Tratamento                                                        | Verificação                                  |
| --- | ------------------ | ----------------------------------------------------------------- | -------------------------------------------- |
| 8   | Lista e quadro     | Chip só nas marcadas para o cartão, 1 chamada por página          | ✓ `[V]` 3 chips, 1 chamada · `[T]` card_only |
| 9   | Tabela             | Uma coluna por propriedade ativa, com provedor de contexto        | ✓ `[V]` cabeçalhos e células, 1 chamada      |
| 10  | Calendário         | Sem interação — construído sobre `start_date`/`target_date`       | ✓ `[I]` fora de escopo declarado             |
| 11  | Cronograma         | Idem                                                              | ✓ `[I]` fora de escopo declarado             |
| 12  | Nível de workspace | Coluna e chip não aparecem: projetos têm configurações diferentes | ✓ `[I]` guarda por `projectId`               |
| 13  | Peek               | Mesma seção do painel                                             | ✓ `[V]`                                      |
| 14  | Paginação          | Leitura é por página de tarefas, nunca por tarefa                 | ✓ `[T]` 40 tarefas em 1 consulta             |

## Filtro, ordenação e agrupamento

| #   | Recurso existente          | Tratamento                                                                 | Verificação                                                 |
| --- | -------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 15  | Filtro da API              | `property_<uuid>`, um `Q` por propriedade em chamada própria               | ✓ `[T]` test_two_properties_at_once_do_not_collide          |
| 16  | Filtro forjado             | UUID validado e propriedade conferida antes de tocar o ORM                 | ✓ `[T]` test_a_forged_filter_never_becomes_a_query          |
| 17  | Ordenação                  | `property__<uuid>` resolvido antes da allowlist, pela coluna tipada        | ✓ `[T]` test_number_sorts_as_number                         |
| 18  | Ordenação forjada          | Quatro entradas forjadas, nenhuma passa                                    | ✓ `[T]` test_a_forged_order_by_falls_back_to_the_default    |
| 19  | Tarefa sem valor           | Vai para o fim nas duas direções                                           | ✓ `[T]` test_work_items_without_value_go_last…              |
| 20  | Agrupamento                | Seleção única no menu "Agrupar por"; uma coluna por opção, "Nenhum" no fim | ✓ `[V]` Indicação 2 · Anúncio 2 · Nenhum 8 · `[T]` grouping |
| 21  | Filtro pela interface      | Seleção no seletor de filtro, com as cores das opções                      | ✓ `[V]` 33 → 2 cartões, chip "Canal is Indicação"           |
| 21b | Filtro que sobrevive ao F5 | A condição volta do servidor e é reidratada, não descartada                | ✓ `[V]` chip presente após recarregar                       |
| 21c | Árvore `and`/`or`/`not`    | Subconsulta por propriedade — duas na mesma folha não colidem              | ✓ `[T]` test_two_properties_in_one_and_node                 |
| 21d | Filtro do produto junto    | Propriedade e prioridade na mesma árvore                                   | ✓ `[T]` test_property_condition_combines_with_a_product…    |
| 21e | Propriedade desligada      | Visão salva com ela não derruba a tela: a condição é descartada            | ✓ `[T]` test_inactive_property_filters_nothing…             |
| 21f | Valor apagado              | Para de contar — a subconsulta filtra `deleted_at`, a junção não filtrava  | ✓ `[T]` test_deleted_value_stops_counting                   |

## Saída do dado

| #   | Recurso existente    | Tratamento                                              | Verificação                                                           |
| --- | -------------------- | ------------------------------------------------------- | --------------------------------------------------------------------- |
| 22  | Exportação CSV/XLSX  | Uma coluna por propriedade, em texto legível            | ✓ `[T]` test_the_export_carries_a_column…                             |
| 23  | Custo da exportação  | Uma consulta de valores para o arquivo inteiro          | ✓ `[T]` test_the_export_reads_values_in_one_query                     |
| 24  | API pública          | Só leitura; aceita leitura em bloco pelo contexto       | ✓ `[T]` test_the_public_api_carries_the_values                        |
| 24b | Definições na API    | Endereço próprio, só leitura, na ordem da tela          | ✓ `[T]` test_the_public_api_serves_the_definitions                    |
| 24c | Escrita de definição | 405 — configuração de projeto tem um caminho só         | ✓ `[T]` test_the_public_api_definitions_are_read_only                 |
| 24d | Projeto alheio       | A lista é do projeto pedido, e só dele                  | ✓ `[T]` test_the_public_api_does_not_serve_another_project            |
| 25  | Webhook              | Carrega os valores no payload                           | ✓ `[T]` test_the_webhook_payload_carries_the_values                   |
| 25b | Webhook se explica   | Leva a definição dos campos que a tarefa usa            | ✓ `[T]` test_the_webhook_payload_explains_itself · `[V]` payload real |
| 25c | Recorte do payload   | Só as propriedades preenchidas, não as 30 do projeto    | ✓ `[T]` test_the_webhook_only_carries_what_the_work_item_uses         |
| 25d | Custo do payload     | Uma consulta de valores por tarefa, não duas            | ✓ `[T]` test_the_webhook_reads_values_once_per_work_item              |
| 25e | Lote                 | Cada tarefa leva as suas — o cache é por tarefa         | ✓ `[T]` test_each_work_item_gets_its_own_definitions                  |
| 25f | Campo excluído       | Para de sair, mesmo antes de a cascata assíncrona rodar | ✓ `[T]` test_a_deleted_property_stops_appearing                       |
| 26  | Espaço público       | Não expõe — o que é interno não vaza por acidente       | ✓ `[I]` fora de escopo declarado                                      |
| 27  | Atividade            | Uma linha por mudança, com o rótulo e não o id da opção | ✓ `[T]` test_changing_a_value_writes_activity                         |

## Outros recursos

| #   | Recurso existente     | Tratamento                                                      | Verificação                                     |
| --- | --------------------- | --------------------------------------------------------------- | ----------------------------------------------- |
| 28  | **Tarefa recorrente** | A ocorrência copia os valores, na árvore inteira                | ✓ `[T]` test_custom_property_values_come_along  |
| 29  | Custo da recorrência  | Em bloco: o custo por nó continua em 8                          | ✓ `[T]` test_custom_properties_do_not_raise…    |
| 30  | Concluir tarefa       | Obrigatória nunca barra (ADR 0009)                              | ✓ `[T]`                                         |
| 31  | Ciclo e módulo        | Sem interação: propriedade descreve a tarefa, não onde ela roda | ✓ `[I]`                                         |
| 32  | Triagem               | Mesma criação, mesma obrigatoriedade                            | ✓ `[I]`                                         |
| 33  | Exclusão lógica       | Junções filtram `deleted_at` explicitamente                     | ✓ `[T]` test_a_deleted_work_item_does_not_count |
| 34  | Fuso do projeto       | Tipo data usa data pura, sem hora — sem ambiguidade de fuso     | ✓ `[I]` `DateField`                             |
| 35  | Permissões            | Configurar é admin; preencher é de quem edita; ler é de todos   | ✓ `[T]` test_configuring_is_an_admin_door       |
| 36  | i18n                  | Chaves em `issue_properties.*`, pt-BR                           | ✓ CI verde                                      |

## Lacuna

Uma só, e ela é de **tipo**, não de esforço.

Agrupar e filtrar **funcionam no backend** e estão testados — quem chama a API
faz as duas coisas hoje. O que falta é o **seletor visual**, e ele esbarra em
`TIssueGroupByOptions` e `WORK_ITEM_FILTER_PROPERTY_KEYS`, que são uniões
fechadas em `@plane/types`. O menu de agrupar, os layouts de quadro e lista e o
pacote de filtros ricos são tipados sobre elas, e a chave de condição é um tipo
literal `${propriedade}__${operador}`.

Uma propriedade personalizada é um id que só existe em tempo de execução. Para
caber ali, a união teria de ser alargada para `string` — o que atravessa toda a
filtragem, o agrupamento e as visões salvas, com risco de regressão em todos os
layouts. É refatoração de tipos no pacote compartilhado, e merece decisão
própria em vez de carona.

Nada disso bloqueia o uso do que foi entregue: os campos existem, guardam,
mostram no cartão e na tabela, ordenam, exportam, viajam no webhook e na API, e
acompanham a recorrência.
