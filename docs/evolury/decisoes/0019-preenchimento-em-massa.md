# ADR 0019 — Preencher campos de muitas tarefas de uma vez

- **Status:** Aceito (20/08/2026)
- **Relacionado:** [ADR 0011](0011-propriedades-personalizadas.md) (propriedades personalizadas), [ADR 0016](0016-um-responsavel-por-tarefa.md) (um responsável), [ADR 0018](0018-exclusao-em-massa.md) (exclusão em massa), [ADR 0012](0012-automacoes-personalizadas.md) (automações)

## Contexto

Depois do ADR 0018, a barra da seleção tinha "Concluir" e "Excluir". Faltava o
que mais se pede numa lista grande: **preencher**. Selecionar trinta tarefas e
dizer que a prioridade de todas é alta, ou que o Canal de todas é Indicação.

Metade disso já estava no repositório — a metade do cliente:

| Peça                                                                                                           | Situação                           |
| -------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| `bulkOperations` → `POST …/bulk-operation-issues/`                                                             | pronta                             |
| Store `bulkUpdateProperties`, com atualização otimista                                                         | pronta                             |
| Tipo `TBulkIssueProperties` (9 campos)                                                                         | pronto                             |
| Códigos de erro **e mensagens traduzidas** (`INVALID_ISSUE_START_DATE` 4101, `INVALID_ISSUE_TARGET_DATE` 4102) | prontos                            |
| Seletores de estado, prioridade, responsável, data                                                             | prontos                            |
| Editor de valor de propriedade personalizada                                                                   | pronto, e feito para ser remontado |
| **O endpoint**                                                                                                 | não existia — é da edição paga     |
| Componente que usasse qualquer disso                                                                           | nenhum                             |

## Como o Plane Cloud faz

A [documentação](https://docs.plane.so/core-concepts/issues/bulk-ops) descreve a
barra em Lista e Planilha, com estado, prioridade, responsável, ciclo, tipo,
etiquetas, módulos e datas. Um detalhe de desenho importa: as mudanças ficam
represadas até um botão **Update** — _"until you click this button, your changes
won't be saved"_. Não é seletor que aplica na hora.

A documentação **não diz** se etiqueta soma ou substitui, nem o que aparece
quando as tarefas escolhidas têm valores diferentes. São as duas decisões
difíceis, e é fora do Plane que elas foram estudadas.

## A decisão

**1. Campo de lista tem modo, e o padrão é acrescentar.** O Jira substituía por
padrão e o efeito foi tanta gente apagando etiqueta achando que estava somando
que virou chamado clássico ([JRA-30729](https://jira.atlassian.com/browse/JRA-30729));
hoje o [Jira Cloud oferece os modos explícitos](https://support.atlassian.com/jira-software-cloud/docs/edit-multiple-issues/).
Aqui são três — **Acrescentar, Remover, Substituir** — com acrescentar
pré-selecionado. O store do front, aliás, já somava.

**2. Responsável não tem modo.** Uma tarefa tem UM responsável (ADR 0016),
garantido por índice único: atribuir em massa é substituir. Pedir dois devolve
`SINGLE_ASSIGNEE_ONLY`, e não um erro de banco.

**3. As mudanças ficam represadas até "Aplicar".** É o desenho da nuvem, e é o
que dispensa diálogo de confirmação: o botão é o freio. Seletor que aplica na
hora, sobre trinta tarefas, é irreversível por acidente.

**4. Campo com valores diferentes abre em "Vários".** Abrir no valor da primeira
tarefa é como se apaga o das outras sem perceber.

**5. Campo que a seleção não pode receber não aparece.** Estado, responsável,
etiqueta e propriedade personalizada são DO PROJETO. Numa seleção que atravessa
projetos — "Minhas tarefas", visões do espaço —, sobram prioridade e datas, com
uma linha explicando por quê.

**6. Recusa inteira, nunca parcial**, como no ADR 0018 e como o arquivamento em
massa do upstream já fazia. Data é conferida **por tarefa e contra o que a
tarefa já tem**: comparar a data pedida com o vazio deixaria passar um início
posterior a um vencimento que ninguém tocou.

**7. Histórico por tarefa, sem notificação por item.** O `issue_activity` de
sempre — e com ele vêm de graça o tempo real (ADR 0013) e as automações (ADR
0012), que penduram no mesmo ponto. Notificar item a item transformaria um
preenchimento de duzentas tarefas em duzentos avisos.

**8. Propriedade personalizada tem endpoint próprio**, e ele escreve tarefa a
tarefa de propósito: `gravar_valor` valida por tipo e `registrar_atividade_de_propriedade`
escreve o histórico e acorda as automações. Reproduzir isso em bloco criaria um
segundo caminho para o mesmo destino — e é assim que dois caminhos divergem. O
que é feito **uma vez só** é a conferência do valor: recusar na décima tarefa
deixaria nove preenchidas e vinte e uma não.

**9. Ciclo e módulo não passam pelo endpoint novo.** Os endpoints deles já
aceitam lista de tarefas e já gravam a atividade com o tipo certo
(`cycle.activity.created`).

## Sem desfazer, e por quê

A exclusão em massa ganhou desfazer porque o instante do lote bastava para achar
o que devolver. Uma edição precisaria guardar o valor anterior **de cada
tarefa**. O histórico já registra _de → para_ por item, e refazer à mão é
possível — ao contrário de uma exclusão. Se um dia fizer falta, o caminho
natural é "reverter este lote" lendo as próprias linhas de histórico, e isso é
uma funcionalidade por si só.

## Consequências

- **Custo de sincronia**: um endpoint novo, um POST acrescentado a uma rota que
  já existia, o campo `modes` no tipo do payload e o store respeitando o modo.
  Nenhuma migração.
- **`updated_by` passou a ser gravado na edição em massa.** `bulk_update` não
  passa pelo `save()`, e sem pôr o campo na lista uma edição em massa não teria
  autor no registro da tarefa — o upstream deixa assim no arquivamento em massa.
- **Uma edição em massa acorda as automações uma vez por tarefa.** É o
  comportamento certo — uma regra que reage a mudança de estado tem de reagir —,
  mas trezentas tarefas são trezentas avaliações, e uma automação pode mudar a
  tarefa de novo.
- **Mudar vencimento em massa move tarefas de etapa** na varredura seguinte
  (ADR 0014).
- **Fora de escopo**: copiar tarefas entre projetos e inscrever-se em massa, que
  a nuvem oferece e ninguém pediu.
