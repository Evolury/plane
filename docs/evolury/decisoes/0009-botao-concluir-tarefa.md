# ADR 0009 — Botão de concluir tarefa

- **Status:** Aceito (12/08/2026)
- **Contexto:** funcionalidade [concluir-tarefa](../funcionalidades/concluir-tarefa/backlog.md)
- **Relacionado:** [ADR 0001](0001-minhas-tarefas-overlay-pessoal.md) (overlay pessoal)

## Contexto

No Plane não existe "concluir": existe o **grupo** de estado `completed`, e
cada projeto pode ter vários estados dentro dele. Concluir é arrastar o cartão
ou trocar o estado pelo seletor. Plataformas como o Asana oferecem um botão
único, e é isso que o produto precisa.

O levantamento no código mostrou três fatos que moldam a decisão:

1. **Tudo que depende de conclusão lê o grupo do estado**, nunca um campo
   próprio: progresso de ciclo e módulo, gráficos, arquivamento automático.
   Se a conclusão continuar sendo uma troca de estado, nada disso muda.
2. **Não há regras de transição de estado neste fork** (o modelo de workflow é
   da edição paga). O botão não precisa validar transições.
3. A automação de fechamento existente escolhe o destino com
   `project.default_state`, que na verdade significa "estado dos itens novos" —
   reaproveitá-la para conclusão seria herdar uma confusão semântica.

## Decisão

**O botão não é um caminho novo.** Ele dispara exatamente a mesma atualização
de estado que o seletor já faz. Não há endpoint próprio, nem campo
`is_completed`, nem fluxo paralelo. Assim, histórico de atividade, webhooks,
notificações, contadores de ciclo e módulo e análises continuam corretos sem
nenhuma adaptação — pelo simples motivo de que nada mudou para eles.

O que o botão acrescenta é **uma regra de destino**:

- o projeto ganha um campo **`completion_state`**, configurável na página de
  Estados;
- sem configuração, resolve para o estado de menor `sequence` dentro do grupo
  concluído — funciona em qualquer projeto sem ninguém configurar nada;
- `default_state` **não** é reaproveitado: ele responde por outra pergunta.

**Sem interruptor de automação.** Automação é regra que roda sozinha em
segundo plano; isto é um botão que a pessoa aperta, e cujo efeito ela poderia
obter pelo seletor de estado. Um interruptor criaria projetos com e sem o
botão, sem ganho. Configurável é o destino, não a existência do botão.

**Reabrir** restaura o último estado não concluído lido do histórico de
atividade; sem histórico, cai no estado padrão do projeto.

## Exceção deliberada ao ADR 0001

O ADR 0001 fixou que a etapa pessoal de "Minhas tarefas" e o estado real do
item não se afetam. Concluir passa a ser **exceção de mão única**: ao entrar
no grupo concluído, a associação pessoal de cada responsável vai para a etapa
dele no grupo concluído; mover a etapa pessoal continua sem alterar nada no
projeto.

Sem isso, uma tarefa concluída ficaria parada em "Hoje" na lista de quem a
tem atribuída. A direção única preserva o que motivou o ADR 0001 — organização
pessoal não vaza para o time —, enquanto deixa o fato compartilhado
(a conclusão) se refletir na visão pessoal.

Regras que completam a exceção:

- **Quem já está numa etapa do grupo de destino fica onde está.** Se a pessoa
  escolheu uma etapa própria de concluídas, é dela a última palavra.
- **Sem associação, a tarefa encerrada pertence à etapa do grupo
  correspondente.** Isso é resolvido na listagem, não gravado — cobre quem
  nunca moveu nada e o que foi encerrado antes de a pessoa ter etapas, sem
  migração e sem inventar associação para ninguém.
- **Andar entre grupos abertos não mexe em nada.** O time mover o estado de
  "A fazer" para "Em andamento" é fluxo do projeto, e não diz nada sobre a
  organização pessoal de ninguém.

### Revisão de 13/08/2026 — o ciclo inteiro, não só a conclusão

A primeira versão desta decisão dizia que reabrir **não** desfaz o movimento,
com o argumento de que devolver a tarefa à etapa anterior exigiria guardar de
onde ela veio. O argumento continua correto, mas a conclusão estava errada: o
destino da reabertura não precisa ser a etapa anterior — é a **etapa padrão**,
exatamente como o projeto devolve a tarefa ao estado padrão. Sem memória
nenhuma.

Com isso a etapa pessoal acompanha o ciclo inteiro, com a mesma regra do
projeto traduzida para etapas:

| Transição do estado real                   | Destino da etapa pessoal                         |
| ------------------------------------------ | ------------------------------------------------ |
| entrou no grupo concluído                  | etapa de conclusão (a marcada, senão a primeira) |
| entrou no grupo cancelado                  | primeira etapa do grupo cancelado                |
| voltou para o estado **padrão** do projeto | etapa padrão, como uma recém-atribuída           |
| voltou para qualquer outro estado aberto   | primeira etapa do grupo desse estado             |

As duas últimas linhas parecem uma só, mas não são, e a diferença é o que a
pessoa quis dizer. O **botão de reabrir** manda a tarefa para o estado padrão do
projeto, e ali "de volta ao começo" é a resposta certa. Já quem escolhe
"Em andamento" no **campo de estado** está dizendo onde a tarefa está — a etapa
pessoal segue essa escolha, e não o começo da fila. É a mesma informação que
distingue os dois caminhos no servidor, que não sabe (nem precisa saber) por
qual controle da tela a mudança passou.

Duas peças novas sustentam a tabela: **`WorkStage.is_completion`**, que responde
"qual destas etapas concluídas é o destino" — a mesma pergunta que
`Project.completion_state` responde do lado do projeto —, e uma etapa
**"Canceladas"** no seed, sem a qual o cancelamento não teria onde aterrissar.
Quem já tinha etapas semeadas recebe as duas por migração.

A mão única continua valendo, e é o que importava no ADR 0001: mover a etapa
pessoal segue sem alterar nada no projeto.

## Escopo

Épicos e tarefas recorrentes **ficam de fora**, por não existirem nesta
edição: o backend não tem endpoint de épico nem a flag `is_epic_enabled`
(só o campo `IssueType.is_epic`, herdado), e de recorrentes não há nada além
de chaves de tradução órfãs. A interface de ambos existe no front porque o
código é compartilhado com a edição paga. Recorrentes entram no roadmap
próprio, depois desta entrega.

Também ficam de fora, por não terem o botão: itens em triagem pendente,
rascunhos, itens arquivados e os quadros públicos.

## Consequências

- Concluir passa a existir em massa também, já que o Plane tem seleção
  múltipla e o botão usa o caminho de atualização comum.
- O tratamento visual de concluído precisa valer nos cinco layouts e em
  Minhas tarefas, senão a interface fica contraditória.
- A correção do escopo cruzado na automação de fechamento
  (`State.objects.filter(group="cancelled").first()` sem filtrar por projeto)
  entra junto, por ser da mesma área.
