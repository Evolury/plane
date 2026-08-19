# ADR 0016 — Um responsável por tarefa

- **Status:** Aceito (19/08/2026)
- **Contexto:** funcionalidade [um-responsavel](../funcionalidades/um-responsavel/especificacao.md)
- **Relacionado:** [ADR 0001](0001-minhas-tarefas-overlay-pessoal.md) (overlay pessoal), [ADR 0010](0010-tarefas-recorrentes.md) (recorrentes), [ADR 0012](0012-automacoes-personalizadas.md) (automações)

## Contexto

Uma tarefa aceitava vários responsáveis. O pedido foi que aceitasse **um, e nunca
mais de um** — não como preferência de tela, mas como regra do sistema.

Antes de mudar, era preciso entender por que o Plane faz diferente. A resposta
importa: mudar o que se entende é barato, mudar o que não se entende é como o
defeito entra.

## Por que o Plane permite mais de um

A [documentação pública](https://docs.plane.so/core-concepts/issues/overview)
não explica — só usa o plural. O código explica, em três lugares independentes:

**1. É decisão de origem.** A tabela `IssueAssignee` está na migração
`0001_initial.py`, de 26/10/2022. Nunca houve fase de responsável único da qual
o produto tenha saído.

**2. Responsável é faceta, não dono.** Em `plane/utils/grouper.py`,
`assignee_ids` é montado pela mesma maquinaria de `ArrayAgg` que monta
`label_ids` e `module_ids`, e o `FIELD_MAPPER` manda os três para junções M2M.
Agrupar por responsável **duplica a linha** entre colunas, como agrupar por
etiqueta.

O contraste é a prova: o mesmo código tem campos com forma de dono —
`Project.default_assignee`, `Module.lead`, `Cycle.owned_by`, todos FK singulares.
A escolha foi deliberada: **o projeto tem dono; a tarefa tem um conjunto de
gente**.

**3. O conjunto acumula um segundo papel: audiência.** Cada responsável
acrescentado vira também um `IssueSubscriber`, e continua inscrito depois de
removido; a notificação é classificada como `assigned` ou `subscribed` conforme
a pessoa esteja no conjunto.

Em uma frase: no Plane, "responsáveis" responde _"quem está trabalhando
nisto?"_ — pergunta de muitos valores — e não _"de quem é isto?"_. É o modelo do
GitHub e do Jira. O custo é a responsabilidade difusa, que é o que se quis
eliminar.

## A decisão

**A garantia mora no banco.** Um índice único parcial em
`issue_assignees(issue_id) WHERE deleted_at IS NULL`, e o par correspondente nos
rascunhos. Dois responsáveis deixam de ser possíveis — não "não oferecidos":
vale para tela, API pública, importação e SQL direto.

### Por que não trocar o M2M por chave estrangeira

Seria o modelo "certo" no papel. Custaria reescrever todo caminho de leitura
(agrupamento, filtros, análises, exportação, webhook, quadro público), quebrar o
contrato da API pública — `assignees` deixaria de ser vetor — e o formato de
`IssueVersion.assignees`, que é o retrato do histórico. E criaria conflito em
**toda** sincronização com o upstream, para sempre (ver [UPSTREAM.md](../../../UPSTREAM.md)).

A garantia obtida seria exatamente a mesma. Os caminhos de leitura seguem
intocados, operando com vetores de tamanho ≤ 1.

### Ao receber mais de um, fica o último

Decisão do Tássio, **contra a recomendação** de recusar com 400. O argumento
contra: integração que manda dois perde uma pessoa sem ficar sabendo, e log é
lido por ninguém.

Fica registrado, e o risco foi mitigado dentro da escolha: a resposta devolve o
`assignee_ids` efetivo, então quem comparar o que enviou com o que voltou enxerga
a diferença. E o histórico da tarefa passou a ler o **banco**, não o pedido —
antes anunciava as duas pessoas quando só uma tinha sido gravada.

Onde a normalização entra importa: as validações de "é membro do projeto?"
reordenam a lista pelo que o banco devolve. Por isso `apenas_um()` roda **antes**
delas — "fica o último" tem de valer sobre o que quem chamou mandou, não sobre a
ordem da tabela.

### Responsável continua opcional

Tarefa nasce sem dono e ganha um depois, que é como triagem funciona.

## Consequências

- **O overlay pessoal degenera para uma pessoa.** O ADR 0001 previa a mesma
  tarefa em etapas diferentes para pessoas diferentes; com um responsável, cada
  tarefa alcança uma. A maquinaria continua por pessoa — `WorkStage` é por
  (workspace, dono) — mas o caso de duas pessoas na mesma tarefa deixou de
  existir. Um teste que provava exatamente isso teve de mudar de premissa.
- **Agrupar por responsável deixa de duplicar cartão.**
- **A automação perde o modo "somar"**: com um responsável, somar e definir são
  a mesma coisa. Sobra escolher alguém ou não escolher ninguém.
- **A suíte roda com `--nomigrations`** e nunca executa migrações. Descobrimos
  isso porque a primeira injeção de defeito — tirar a trava da migração — não
  derrubou nada. Por isso a regra de colapso foi extraída para `excedentes()`,
  que tem teste, e a migração foi verificada rodando contra a instância real.
