# Tarefa recorrente — Backlog de implementação

Decisão: [ADR 0010](../../decisoes/0010-tarefas-recorrentes.md).
Especificação: [especificacao.md](especificacao.md).
Plano aprovado em 13/08/2026, com as sete recomendações.

## F0 — Documentação

- [x] ADR 0010 (decisão, alternativas, consequências)
- [x] Especificação
- [x] Backlog (este arquivo)

## F1 — Motor e dados (sem interface)

- [x] F1.1 `python-dateutil` como dependência **declarada** da API — hoje só
      existe por transitividade, que foi como o `live` caiu em 13/08
- [x] F1.2 Modelos `RecurringWorkItem` (agenda + molde) e
      `RecurringWorkItemOccurrence` (data prevista → tarefa criada), com
      unicidade por (regra, data prevista) para idempotência
- [x] F1.3 Migração
- [x] F1.4 Cálculo da próxima data com `dateutil.rrule`, incluindo o recuo para
      o último dia do mês quando o dia escolhido não existe
- [x] F1.5 Geração: guarda de ocorrência aberta, fim da recorrência, atraso que
      não acumula, ator = autor da regra, sem passar por triagem
- [x] F1.6 Job no Celery beat, a cada 15 minutos
- [x] F1.7 Testes de contrato: cada frequência, virada de mês (28/29/30/31),
      intervalo maior que 1, fim por data e por contagem, idempotência sob
      repetição, guarda de ocorrência aberta, modo após conclusão

O motor fica **inerte** até a F2: sem interface não há como criar regra, e o
job varre uma tabela vazia. É de propósito — dá para revisar o cálculo com
calma antes de existir gente dependendo dele.

## F2 — Configurações

- [x] F2.1 Item "Tarefas recorrentes" na categoria Execução, só para admin
- [x] F2.2 Lista das regras do projeto, com próxima ocorrência visível
- [x] F2.3 Formulário de agenda e molde, reaproveitando as chaves órfãs
      `recurring_work_items.*`
- [x] F2.4 Pré-visualização das próximas datas ("próximas: 18/08, 25/08, 01/09")
      — é o que torna uma regra complexa confiável
- [ ] F2.5 Aviso quando o responsável do molde não é mais membro do projeto
- [x] F2.6 Ligar/desligar a regra sem excluí-la

## F3 — Integração

- [ ] F3.1 Rastro na tarefa gerada ("criada pela recorrência X")
- [ ] F3.2 Modo "após conclusão" ligado ao botão de concluir (ADR 0009)
- [ ] F3.3 "Tornar esta tarefa recorrente", a partir de uma tarefa existente

## Ciclo seguinte

- [ ] Subtarefas no molde, com regra própria para o que acontece quando a
      ocorrência anterior tem subtarefa aberta

## Fora de escopo

Anexos no molde, pular uma ocorrência sem mexer na série, feriado e dia útil
(ADR 0010).
