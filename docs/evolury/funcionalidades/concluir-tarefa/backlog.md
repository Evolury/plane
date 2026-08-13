# Concluir tarefa — Backlog de implementação

Decisão: [ADR 0009](../../decisoes/0009-botao-concluir-tarefa.md).
Plano aprovado em 12/08/2026, com todas as recomendações.

## T0 — Documentação

- [x] ADR 0009 (decisão, exceção ao ADR 0001, escopo)
- [x] Backlog (este arquivo)

## T1 — Backend: destino da conclusão

- [x] T1.1 Campo `completion_state` em `Project` (FK para `State`,
      `on_delete=SET_NULL`), migração e serializer
- [x] T1.2 Resolvedor `get_completion_state(project)`: usa `completion_state`
      quando definido; senão, o estado de menor `sequence` no grupo
      `completed` **do próprio projeto**
- [x] T1.3 Corrigir o escopo cruzado da automação existente: em
      `issue_automation_task.close_old_issues`, o fallback
      `State.objects.filter(group="cancelled").first()` não filtra por projeto
      e pega o estado de qualquer projeto do banco
- [x] T1.4 Testes de contrato: resolvedor com e sem configuração, estado
      configurado fora do grupo, projeto sem estado concluído, e exclusão do
      estado escolhido — que revelou que `State` é excluído logicamente, então
      o `SET_NULL` nunca dispara e o resolvedor precisa checar `deleted_at`

Sem endpoint novo: o botão usa o `PATCH` de work item que já existe.

## T2 — Botão e estado visual

- [x] T2.1 Componente de conclusão reutilizável (alterna concluir/reabrir),
      chamando o mesmo caminho de atualização de estado do seletor; aplicado
      no cabeçalho do peek
- [x] T2.2 Reabrir devolve ao estado padrão do projeto (o mesmo de um item
      novo), com recuo para o primeiro estado em aberto por `sequence`.
      **Desvio consciente do ADR**: a leitura do histórico de atividade exigiria
      buscar as atividades de cada item só para desenhar um botão, o que não se
      paga nos layouts de lista — o destino previsível venceu
- [x] T2.3 Confirmação ao concluir tarefa com subtarefas abertas, com a opção
      de concluir as subtarefas junto. Só as subtarefas **diretas**; quem tem
      filha aberta é perguntado por sua vez, ao ser concluída.
      A validação revelou que o peek se fechava ao primeiro clique dentro da
      confirmação — o modal é portado para fora do painel, então o detector de
      clique externo o tratava como clique de fora, e o botão desmontava antes
      do `click` disparar (nenhuma requisição saía). A loja de detalhe ganhou
      `isCompletionModalOpen`, como os outros modais do peek já faziam
- [x] T2.4 Regras de exibição: permissão, arquivado e rascunho no peek.
      Triagem e quadro público não passam por este cabeçalho — a triagem tem
      página própria e o quadro público é outro aplicativo
- [x] T2.5 Tratamento visual de concluído nos **cinco layouts** (esmaecido, via
      o grupo do estado — mesma fonte que o resto do produto). Na planilha vai
      na linha inteira, e não só na célula do título
- [x] T2.6 Ação em massa: concluir a seleção. A seleção múltipla existia
      inteira no código desta edição, mas vinha **desligada**
      (`useBulkOperationStatus` fixo em `false`) porque a única ação oferecida
      era uma faixa de upsell. Agora há ação real, então a seleção liga e a
      faixa dá lugar à barra de conclusão. Sem endpoint de operação em massa
      (é da edição paga), a barra repete a mesma atualização item a item, em
      lotes de cinco

## T3 — Minhas tarefas

- [x] T3.1 Ao entrar no grupo concluído, mover a associação pessoal de cada
      responsável para a etapa dele no grupo concluído. O gancho fica em
      `update_issue_activity`, o funil por onde passam TODOS os caminhos que
      mudam estado — botão, seletor, arrastar, API externa, automação de
      fechamento —, o mesmo de que notificações e webhooks já dependem.
      Complemento na listagem: tarefa concluída **sem associação** aparece na
      etapa de concluídas, o que cobre quem nunca moveu nada e o que foi
      concluído antes de existirem etapas, sem migração
- [x] T3.2 Preservar quem já está numa etapa concluída (não reposicionar)
- [x] T3.3 Garantir a mão única: mover etapa pessoal continua sem alterar o
      estado real (regressão do ADR 0001)
- [x] T3.4 Tratamento visual de concluído também nesta página — sai de graça,
      a página usa os mesmos blocos de lista e quadro

## T4 — Configuração

- [x] T4.1 Escolha do estado de conclusão na página de Estados do projeto, no
      mesmo lugar do "Marcar como padrão" e só nos estados do grupo concluído —
      é a mesma pergunta com outro sujeito. O rótulo mostra "Conclusão" também
      quando o destino é o automático, em vez de deixar a resposta invisível
- [x] T4.2 Comportamento ao excluir o estado escolhido (volta ao automático).
      Some com a validação de entrada: o estado precisa ser do próprio projeto
      e do grupo concluído — e o resolvedor ignora o que não for, como última
      linha
- [x] T4.3 (surgiu na validação) `completion_state` no endpoint de listagem de
      projetos. A lista usa `.values()` com colunas fixas, não o serializer, e
      é ela que alimenta o `projectMap` do front em qualquer página — sem o
      campo, o botão **sempre** caía no destino automático e a configuração não
      tinha efeito nenhum

## T5 — Validação e entrega

- [x] T5.1 Testes de contrato do backend e suíte completa
- [x] T5.2 `pnpm check`
- [x] T5.3 Visual na stack isolada: concluir e reabrir, subtarefas, massa,
      cinco layouts e Minhas tarefas
- [x] T5.4 Conferir que ciclo, módulo e gráficos refletem a conclusão sem
      alteração de código (o objetivo do ADR 0009). Confirmado no ciclo de
      validação: 4 tarefas, 1 concluída, contada pelo grupo do estado — nenhuma
      linha de código de ciclo foi tocada nesta entrega
- [ ] T5.5 PR, CI, merge e deploy
- [ ] T5.6 CHANGELOG + release

## Dois enganos que só a tela pegou

Ambos passavam nos testes e falhavam no uso — vale registrar o padrão.

1. **UUID contra texto.** O reposicionamento em segundo plano recebe os ids do
   payload JSON, ou seja, como TEXTO; os testes chamavam a função com objetos
   `UUID`. A comparação de grupo dava sempre "nada mudou" e nada era
   reposicionado. Agora há teste com id em texto, que é como o chamador real
   funciona.
2. **Campo ausente na listagem de projetos.** A configuração era gravada e lida
   corretamente no banco, mas o front nunca a via. Ver T4.3.

## Achados fora de escopo

- O cronograma (gantt) mostra o cabeçalho de datas e a duração em inglês:
  `9 days`, `Week 32`, `Aug 2026`, iniciais dos dias. Também `getBlockViewDetails`
  monta `From …` / `Till …`. Não é desta entrega, mas é do mesmo tipo de
  pendência de idioma já corrigida em outros lugares.

## Fora de escopo

Épicos e tarefas recorrentes, por não existirem nesta edição (ADR 0009).
Recorrentes têm roadmap próprio, depois desta entrega.
