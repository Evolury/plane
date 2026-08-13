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

Duas regras completam a exceção:

- **Quem já está numa etapa do grupo concluído fica onde está.** Se a pessoa
  escolheu uma etapa própria de concluídas, é dela a última palavra.
- **Sem associação, a tarefa concluída pertence à etapa de concluídas.** Isso é
  resolvido na listagem, não gravado — cobre quem nunca moveu nada e o que foi
  concluído antes de a pessoa ter etapas, sem migração e sem inventar
  associação para ninguém.

Reabrir **não** desfaz o movimento: devolver a tarefa à etapa anterior exigiria
guardar de onde ela veio, e mão única foi a decisão.

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
