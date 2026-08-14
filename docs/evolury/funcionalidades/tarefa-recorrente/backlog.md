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
- [~] F2.5 Aviso quando o responsável do molde não é mais membro do projeto —
      **substituído pela F5**: o molde virou tarefa de origem na F4, e o
      tratamento certo tem três camadas, não um aviso
- [x] F2.6 Ligar/desligar a regra sem excluí-la

## F3 — Integração

- [x] F3.0 "Último dia do mês" como opção própria, conferida contra o Asana

- [x] F3.2 Modo "após conclusão" ligado ao botão de concluir (ADR 0009) — a
      primeira ocorrência sai da data de início, e cada conclusão agenda a
      seguinte; sem isto o modo existia no formulário e nunca disparava

F3.1 (rastro) e F3.3 ("tornar recorrente") foram absorvidos pela F4: o rastro
sai da trava, e a porta de entrada virou o desenho inteiro.

## F4 — Revisão: a recorrência mora na tarefa

Decidido em 13/08/2026 (ADR 0010, revisão). Havia **uma regra e uma ocorrência
em produção** quando isto foi escrito — a migração é de dados, não só de esquema.

- [x] F4.1 `source_issue` na regra; campos de molde saem. Migração converte cada
      molde existente numa tarefa de verdade, que passa a ser a origem
- [x] F4.2 `initial_state` na regra (padrão: etapa padrão do projeto) — a
      ocorrência nunca nasce onde a anterior foi concluída
- [x] F4.3 Antecedência em dias: nasce em D-N, com início = D-N e vencimento = D
- [x] F4.4 Geração passa a copiar da tarefa de origem, sem comentários,
      atividade, anexos, ciclo, módulo e relações
- [x] F4.5 Ciclo de vida da origem: concluir segue, arquivar pausa, excluir apaga
- [x] F4.6 Seção "Repetir" no cartão da tarefa, só admin liga
- [x] F4.7 Trava na tarefa gerada, com o rastro ("gerada pela recorrência de X")
- [x] F4.8 Página de configurações vira lista, sem botão de criar
- [x] F4.9 Selo "repete" nos layouts, na tarefa de origem
- [x] F4.10 Aviso quando a antecedência é maior ou igual ao intervalo
- [x] F4.11 Subtarefas na cópia: abertas, sem data, um nível, teto de 50, e a
      trava de recorrência própria
- [x] F4.12 Testes: migração com dado existente, cópia sem os campos individuais,
      datas calculadas, trava na gerada, ciclo de vida da origem, subtarefas
      nascendo sem data e sem herdar nada do ciclo anterior
- [x] F4.13 Antecedência em horas, além de dias — o preparo dentro do dia
      ("a pauta chega 2 horas antes da reunião"); horas valem até 23

## F5 — Responsável que sai do projeto

Decidido em 13/08/2026 (ADR 0010). A remoção **não é travada** e a geração
**não para**; a ordem abaixo é deliberada — primeiro parar o dano, depois
tornar visível, por último o gesto de offboarding, que é o mais caro.

- [x] F5.1 A cópia descarta responsável sem vínculo ativo no projeto — a
      ocorrência nasce sem ele, nunca com um fantasma
- [x] F5.2 Responsáveis inativos expostos na regra (campo derivado no
      serializer), com contador no item "Tarefas recorrentes", linha marcada
      no painel e conserto inline — só para admin do projeto
- [x] F5.3 Confirmação de remoção de membro mostra quantas recorrentes ficam
      afetadas e oferece **transferir** para outra pessoa na mesma tela
- [x] F5.4 Testes: cópia pulando o inativo, contador, e a remoção seguindo
      adiante sem travar
- [x] F5.5 Responsável padrão do projeto na geração — a regra valia em toda
      tarefa criada à mão e era ignorada nas que nascem sozinhas

## F6 — Matriz de compatibilidade (14/08/2026)

- [x] F6.1 Executar a matriz: 40 linhas com evidência
      ([compatibilidade.md](compatibilidade.md))
- [x] F6.2 Corrigir a consulta por regra na listagem, com teto de consultas
      fixado em teste
- [x] F6.3 Precisar "conta em ciclo e módulo" na especificação, no manual e no
      ADR — a ocorrência nasce fora dos dois

- [x] F6.4 Aviso ao arquivar a origem — pausava a série em silêncio
- [x] F6.5 Endpoint `badges/` para o selo do quadro, no lugar da listagem
      completa

## Ciclo seguinte

- [ ] Vencimento relativo da subtarefa: âncora na criação ou no vencimento da
      principal, declarada em vez de deduzida (adição pura sobre a F4)
- [ ] Subtarefa aninhada

## Fora de escopo

Anexos no molde, pular uma ocorrência sem mexer na série, feriado e dia útil
(ADR 0010).
