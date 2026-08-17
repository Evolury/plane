# Automações personalizadas — matriz de compatibilidade

Executada em 16/08/2026, contra o código em `feat/automacoes-personalizadas`.
Mesmo método das anteriores: cada linha é uma interação com um recurso
existente, e cada verificação diz **como** foi comprovada — `[T]` teste
automatizado, `[V]` validação visual em stack local, `[I]` inspeção de código.

Decisão: [ADR 0012](../../decisoes/0012-automacoes-personalizadas.md).

## O caminho de escrita da tarefa

| #   | Recurso existente         | Tratamento                                                            | Verificação                                        |
| --- | ------------------------- | --------------------------------------------------------------------- | -------------------------------------------------- |
| 1   | Editar tarefa pela tela   | Dispara pelo funil único de `issue_activity`                          | ✓ `[V]` prioridade → estado em ~4 s                |
| 2   | Editar pela API pública   | Mesmo funil — os 124 chamadores caem na mesma tarefa Celery           | ✓ `[T]` `TestOFunilUnico`                          |
| 3   | Ações da automação        | Passam pelo `IssueCreateSerializer`: mesma validação que a pessoa     | ✓ `[T]` estado/etiqueta de outro projeto recusados |
| 4   | Arrastar no quadro        | É `partial_update` do mesmo endpoint                                  | ✓ `[T]` `TestOFunilUnico`                          |
| 5   | Rascunho                  | Não dispara: usa `issue_draft.*`, fora do mapa de eventos             | ✓ `[T]` `TestOQueNaoDeveAcontecer`                 |
| 6   | Propriedade personalizada | Gravava `IssueActivity` direto; agora despacha pela mesma função      | ✓ `[T]` casamento por id sobrevive a rename        |
| 7   | Exclusão lógica da tarefa | `Issue.objects` filtra `deleted_at`; regra não age em tarefa excluída | ✓ `[T]` `TestOQueNaoDeveAcontecer`                 |

## Recursos vizinhos

| #   | Recurso existente              | Tratamento                                                                   | Verificação                                     |
| --- | ------------------------------ | ---------------------------------------------------------------------------- | ----------------------------------------------- |
| 8   | Automações fixas (arquivar)    | Convivem: a lista nova fica abaixo das duas caixas                           | ✓ `[V]` captura da tela                         |
| 9   | Tarefas recorrentes (ADR 0010) | Fronteira, não sobreposição: agendado + criar é recusado ao salvar           | ✓ `[T]` mensagem aponta para Recorrentes        |
| 9a  | Ocorrência de recorrência      | Não dispara regra de "tarefa criada" por padrão; interruptor por regra       | ✓ `[T]` padrão e interruptor                    |
| 9b  | Molde de recorrência           | Subtarefa por regra é recusada nele — mudaria todas as ocorrências futuras   | ✓ `[T]` recusa com motivo                       |
| 9c  | Tarefa criada por regra        | Nunca ganha recorrência, nem herda a da origem                               | ✓ `[T]` sem `RecurringWorkItem`                 |
| 10  | Filtro rico do quadro          | **É o mesmo componente e a mesma árvore** — não podem divergir               | ✓ `[V]` seletor abre no editor                  |
| 11  | Propriedades personalizadas    | Entram como gatilho e como condição sem código próprio                       | ✓ `[T]` condição por opção de seleção           |
| 12  | Webhooks                       | Ações emitem atividade normal, então o webhook sai como sempre               | ✓ `[T]` `TestOFunilUnico`                       |
| 13  | Notificações                   | `notification=True` nas ações; a pessoa é avisada como em qualquer mudança   | ✓ `[T]` `TestOFunilUnico`                       |
| 13a | Fila de e-mail                 | O aviso da regra é montável por `create_payload` e vai ao bloco de mensagens | ✓ `[T]` carga montada, `activity_time` presente |
| 14  | Etapas pessoais (ADR 0001)     | Mudança de estado pela regra atravessa `sync_personal_stages_on_completion`  | ✓ `[T]` `TestOFunilUnico`                       |
| 15  | Botão de concluir (ADR 0009)   | É uma mudança de estado — dispara regra de "campo alterado: estado"          | ✓ `[T]` `TestOFunilUnico`                       |
| 16  | Lista de membros               | O robô é `is_bot` e já é excluído das listas por filtros existentes          | ✓ `[T]` `TestORoboForaDasListas`                |
| 17  | Histórico da tarefa            | A linha da automação aparece creditada a "Automação"                         | ✓ `[V]` `is_bot: true` no `actor_detail`        |

## Desempenho

| #   | Cenário                           | Tratamento                                                              | Verificação                              |
| --- | --------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------- |
| 18  | Projeto sem nenhuma automação     | Caminho quente termina num `EXISTS` indexado                            | ✓ `[T]` despacho não enfileira           |
| 19  | Edição que não mexe em campo-alvo | Nem enfileira: sem mudança traduzível, o motor não acorda               | ✓ `[T]` editar o nome não enfileira      |
| 20  | Edição em massa                   | Teto de 200 execuções/hora por regra, com desligamento e motivo gravado | ✓ `[T]` teto e desligamento              |
| 21  | Encadeamento entre regras         | Teto de profundidade 3, verificado na porta                             | ✓ `[T]` acima do teto não enfileira      |
| 22  | Regra que dispara duas vezes      | Criação é idempotente por (regra, origem, nome), com unicidade no banco | ✓ `[T]` 2 disparos, 3 subtarefas · `[V]` |

## Pendências desta matriz

- As linhas 12, 13 e 14 deixaram de ser `[I]` em 17/08/2026 (ver abaixo). O que
  continua valendo daquela nota: uma confirmação **visual** da notificação
  chegando na tela e no e-mail. O teste prende o despacho; ver a pessoa ser
  avisada é outra pergunta, e ela está em aberto.
- Carga real medida em 16/08/2026: 1.000 avaliações drenadas em 10,9 s, mediana
  de 6 ms por avaliação, zero falhas. Detalhes e o achado sobre o teto por hora
  estão no [backlog](backlog.md).

## Três linhas saíram de `[I]` em 17/08/2026

As linhas 5, 7 e 16 afirmavam uma **ausência** — "não dispara", "não alcança",
"não aparece" —, e estavam provadas por leitura de código. Afirmação de ausência
é a que envelhece pior sem teste: no dia em que alguém acrescentar um tipo ao
mapa de eventos ou trocar o manager de uma consulta, nada avisa, e a leitura
antiga continua parecendo correta porque o código que ela leu mudou de lugar.

As três passaram a `[T]`, e a prova de que os testes não são decorativos é a
injeção de defeito: pôr `issue_draft.activity.created` no mapa derruba a linha
5; trocar `Issue.objects` por `all_objects` na condição derruba a linha 7.

As outras seis (2, 4, 12, 13, 14, 15) saíram de `[I]` na mesma passada, e a
forma foi diferente: elas diziam a mesma coisa por caminhos diferentes — "isto
continua funcionando porque a ação passa pelo mesmo lugar que uma edição
humana". Testar cada uma pelo seu chamador seria testar o produto inteiro; o que
sustenta as seis é UM fato, e é ele que ficou preso:

- a ação despacha `issue.activity.updated` com `notification=True` — é desse
  despacho que saem histórico, webhook, notificação e sincronia de etapa
  pessoal, e nenhum deles sabe que houve automação;
- a mesma chamada carrega a origem e a profundidade, que é o que impede o funil
  de virar laço;
- concluir uma tarefa é uma mudança de estado como outra qualquer, com o par que
  prova que a regra **não** acorda com o estado que ela não pediu;
- e o despacho da automação mora DENTRO da tarefa de atividade — se alguém o
  mover para uma view, a afirmação "cai no mesmo lugar" deixa de valer, e o
  teste percebe.

Injeção de defeito: `notification=False` derruba o primeiro; tirar o despacho do
funil derruba o último.

**Nenhuma linha da matriz depende mais de leitura de código.**
