# Um responsável por tarefa — especificação

Uma tarefa tem **um** responsável, e nunca mais de um. Decisões de arquitetura
em [ADR 0016](../../decisoes/0016-um-responsavel-por-tarefa.md).

## A regra

| Onde                  | O que vale                                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Banco**             | índice único parcial em `issue_assignees(issue_id) WHERE deleted_at IS NULL`, e o par nos rascunhos. Dois responsáveis são impossíveis |
| **Portas de escrita** | `apenas_um()` normaliza antes de gravar: chegando dois ou mais, **fica o último**                                                      |
| **Resposta**          | devolve o `assignee_ids` efetivo — quem mandou dois vê que voltou um                                                                   |
| **Histórico**         | lê o banco, não o pedido: registra a atribuição que realmente aconteceu                                                                |

Responsável continua **opcional**: tarefa nasce sem dono e ganha um depois.

## Na tela

- O seletor de responsável é de valor único. Escolher alguém **substitui** quem
  estava; escolher de novo a mesma pessoa esvazia.
- Arrastar um cartão para a coluna de outra pessoa, no quadro agrupado por
  responsável, já substituía antes — segue igual.
- Os rótulos de campo de uma tarefa estão no singular ("Responsável", "Definir
  responsável"). Os de **filtro** seguem no plural: filtrar por responsável pode
  selecionar várias pessoas.

## Na automação

A ação de responsável oferece **uma** pessoa, e perdeu o modo "somar" — com um
responsável, somar e definir são a mesma coisa. A variável `{{responsável}}`
deixou de juntar nomes.

## O que não mudou

`TIssue.assignee_ids` continua vetor, e a API pública continua recebendo e
devolvendo lista. Mexer no tipo espalharia a mudança por dezenas de arquivos sem
ganho, quebraria o contrato externo e o formato do histórico em
`IssueVersion.assignees`. O que mudou é quem escreve nele — e a garantia de que
o vetor tem no máximo um.
