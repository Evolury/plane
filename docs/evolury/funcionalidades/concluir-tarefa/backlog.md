# Concluir tarefa — Backlog de implementação

Decisão: [ADR 0009](../../decisoes/0009-botao-concluir-tarefa.md).
Plano aprovado em 12/08/2026, com todas as recomendações.

## T0 — Documentação

- [x] ADR 0009 (decisão, exceção ao ADR 0001, escopo)
- [x] Backlog (este arquivo)

## T1 — Backend: destino da conclusão

- [ ] T1.1 Campo `completion_state` em `Project` (FK para `State`,
      `on_delete=SET_NULL`), migração e serializer
- [ ] T1.2 Resolvedor `get_completion_state(project)`: usa `completion_state`
      quando definido; senão, o estado de menor `sequence` no grupo
      `completed` **do próprio projeto**
- [ ] T1.3 Corrigir o escopo cruzado da automação existente: em
      `issue_automation_task.close_old_issues`, o fallback
      `State.objects.filter(group="cancelled").first()` não filtra por projeto
      e pega o estado de qualquer projeto do banco
- [ ] T1.4 Testes de contrato: resolvedor com e sem configuração, projeto sem
      estado concluído, e o fallback da automação restrito ao projeto

Sem endpoint novo: o botão usa o `PATCH` de work item que já existe.

## T2 — Botão e estado visual

- [ ] T2.1 Componente de conclusão reutilizável (alterna concluir/reabrir),
      chamando o mesmo caminho de atualização de estado do seletor
- [ ] T2.2 Reabrir: restaura o último estado não concluído lido do histórico
      de atividade; sem histórico, cai no estado padrão do projeto
- [ ] T2.3 Confirmação ao concluir tarefa com subtarefas abertas, com a opção
      de concluir as subtarefas junto
- [ ] T2.4 Regras de exibição: esconder para quem não pode editar estado, e em
      triagem pendente, rascunho, item arquivado e quadro público
- [ ] T2.5 Tratamento visual de concluído (cartão esmaecido, título riscado,
      ícone de check) nos cinco layouts — lista, quadro, planilha, calendário
      e gantt
- [ ] T2.6 Ação em massa: concluir a seleção

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

## Fora de escopo

Épicos e tarefas recorrentes, por não existirem nesta edição (ADR 0009).
Recorrentes têm roadmap próprio, depois desta entrega.
