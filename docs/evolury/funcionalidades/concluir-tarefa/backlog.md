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

- [ ] T3.1 Ao entrar no grupo concluído, mover a associação pessoal de cada
      responsável para a etapa dele no grupo concluído
- [ ] T3.2 Preservar quem já está numa etapa concluída (não reposicionar)
- [ ] T3.3 Garantir a mão única: mover etapa pessoal continua sem alterar o
      estado real (regressão do ADR 0001)
- [ ] T3.4 Tratamento visual de concluído também nesta página

## T4 — Configuração

- [ ] T4.1 Seletor de estado de conclusão na página de Estados do projeto,
      listando só os estados do grupo concluído
- [ ] T4.2 Comportamento ao excluir o estado escolhido (volta ao automático)

## T5 — Validação e entrega

- [ ] T5.1 Testes de contrato do backend e suíte completa
- [ ] T5.2 `pnpm check`
- [ ] T5.3 Visual na stack isolada: concluir e reabrir nos cinco layouts, em
      massa, com subtarefas, em Minhas tarefas, e sem permissão
- [ ] T5.4 Conferir que ciclo, módulo e gráficos refletem a conclusão sem
      alteração de código (o objetivo do ADR 0009)
- [ ] T5.5 PR, CI, merge e deploy
- [ ] T5.6 CHANGELOG + release

## Achados fora de escopo

- O cronograma (gantt) mostra o cabeçalho de datas e a duração em inglês:
  `9 days`, `Week 32`, `Aug 2026`, iniciais dos dias. Também `getBlockViewDetails`
  monta `From …` / `Till …`. Não é desta entrega, mas é do mesmo tipo de
  pendência de idioma já corrigida em outros lugares.

## Fora de escopo

Épicos e tarefas recorrentes, por não existirem nesta edição (ADR 0009).
Recorrentes têm roadmap próprio, depois desta entrega.
