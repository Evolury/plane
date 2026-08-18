# Automações personalizadas — backlog de implementação

Decisão: [ADR 0012](../../decisoes/0012-automacoes-personalizadas.md).
Manual: [manual.md](manual.md).
Plano aprovado em 16/08/2026, com as três respostas do dono do produto:
gatilho agendado **no v1**, ação de criar tarefa **completa**, notificar
**no produto e por e-mail**.

As três fases juntas são o v1 aprovado. Cada uma é publicável sozinha.

## F1 — O motor e a reação

- [x] F1.1 Modelos `Automation` e `AutomationRun`, com índice de despacho
      (projeto + gatilho + ativa) e de histórico (regra + data)
- [x] F1.2 Migração `0143_evolury_automacoes`
- [x] F1.3 `condicao.py` — o "se" como o filtro do produto aplicado a uma tarefa
      só, reusando `FiltroComPropriedades`
- [x] F1.4 `gatilhos.py` — tradução do vocabulário do histórico para o do filtro,
      casamento por **id**, teto de profundidade, autoguarda da regra
- [x] F1.5 `acoes.py` — registro de ações; as seis de campo, todas pelo
      `IssueCreateSerializer`
- [x] F1.6 `ator.py` — usuário-robô por workspace
- [x] F1.7 `despacho.py` — o enxerto único dentro de `issue_activity`, com
      descarte barato
- [x] F1.8 Correção da lacuna das propriedades personalizadas: a gravação de
      valor não passava por `issue_activity` e usava o **nome** como campo
- [x] F1.9 `automation_task.py` — avaliação, execução, registro, teto por hora
- [x] F1.10 `validacao.py` + serializer — regra malformada recusada com frase
- [x] F1.11 API: CRUD, `/runs`, `/simulate`
- [x] F1.12 Declaração em `CELERY_IMPORTS`
- [x] F1.13 Lista na tela de Automações, com a regra **dita em português**
- [x] F1.14 Editor em rota própria: QUANDO / SE / ENTÃO, frase viva, simulação
- [x] F1.15 Painel de execuções
- [x] F1.16 Testes de contrato (32), com defeitos reintroduzidos para provar que
      não são vazios
- [x] F1.17 Verificação visual ponta a ponta no `planedev`

## F2 — O relógio e a voz

- [x] F2.1 Gatilho agendado: `trigger_config` com frequência, dias e horário no
      fuso do produto (ADR 0006); `next_run_at` e tarefa no Celery beat a cada
      15 min, mesma cadência das recorrentes
- [x] F2.2 Execução em lote: uma linha de `AutomationRun` resume a rodada, com
      as tarefas alcançadas em `actions_result`
- [x] F2.3 Ação **comentar**, com a lista fechada de variáveis
      (`{{tarefa}}`, `{{responsável}}`, `{{quem_disparou}}`, `{{estado}}`,
      `{{vencimento}}`) — sem funções, sem aninhamento
- [x] F2.4 Ação **notificar**: `Notification` no sino + fila de e-mail existente
- [x] F2.5 Ação **arquivar**
- [x] F2.6 Ação **incluir no ciclo ativo**
- [x] F2.7 Editor do gatilho agendado, com dias da semana e horário do fuso do projeto

## F3 — Criação e ergonomia

- [x] F3.1 Ações **criar tarefa** e **criar subtarefas**, com idempotência
      garantida pelo banco (`AutomationCreation`, unicidade em regra + origem +
      nome). Redesenhado depois da pesquisa de 16/08: o defeito número um deste
      recurso é **duplicata**, não laço
- [x] F3.2 A combinação _agendada + criar_ **deixou de existir** — recusa ao
      salvar, com a mensagem apontando para Tarefas recorrentes, em vez do aviso
      de tela que estava planejado e que era fraco
- [x] F3.3 `include_recurring`: ocorrência de recorrência não dispara regra de
      "tarefa criada" por padrão, com interruptor por regra
- [x] F3.4 Recusa de subtarefa em tarefa que é origem de recorrência ativa
- [x] F3.5 Herança de responsáveis e vencimento relativo na criação
- [x] F3.6 Catálogo de receitas prontas em `packages/constants`, incluindo as
      duas que ensinam a diferença entre reagir e repetir
- [x] F3.7 Tela do catálogo de receitas no estado vazio. A receita viaja pela
      URL (`?receita=<chave>`), resolvida contra o catálogo — que continua sendo
      a única fonte da verdade — e o editor nasce preenchido
- [x] F3.8 Poda de `AutomationRun` em `cleanup_task.py`, com **duas janelas**:
      30 dias para a execução que fez algo (é o que se audita depois) e 7 dias
      para a que parou na condição (é o que faz volume, e "não casou" repetido
      cinco mil vezes diz o mesmo que uma vez). `AutomationCreation` **fica de
      fora de propósito**: parece log e é a garantia de idempotência — apagá-la
      por idade traria de volta o defeito que ela impede. Ela se limpa pelo
      CASCADE do `hard_delete` da tarefa

## Medição de carga (16/08/2026)

200 tarefas, 5 regras no mesmo campo, uma pegando tudo e quatro de condição
estreita — a edição em massa que motivou o teto por hora.

|                         |                                      |
| ----------------------- | ------------------------------------ |
| Enfileirar 200 edições  | 0,9 s (4,5 ms/tarefa)                |
| Drenar 1.000 avaliações | 10,9 s                               |
| Duração por avaliação   | mediana 6 ms · p95 24 ms · máx 36 ms |
| Falhas                  | 0                                    |

Latência de quem clica: **não medida porque não existe** — o despacho roda dentro
de `issue_activity`, que já é assíncrona, então o caminho do pedido HTTP não
ganhou trabalho nenhum.

A medição achou o que a teoria não tinha mostrado: as três regras de condição
estreita fizeram **200 avaliações e 0 escritas** cada. Com o teto em 200, uma
única edição em massa as desligaria — punindo justamente as regras bem escritas,
por não terem feito nada. O teto subiu para 1.000 e passou a morar em `settings`.

## Corrigido depois da auditoria de 16/08/2026

Dois defeitos encontrados numa auditoria de completude, e não pelos testes —
os dois eram promessas que o produto não cumpria:

- [x] **O e-mail da ação "notificar" não saía.** `create_payload` só monta
      mensagem para registro que tenha `issue_activity`, e descarta o resto em
      silêncio. A carga do aviso passou a incluir a parte que falta, com
      `field: "automation"`, e a montagem ganhou um `pop` próprio que a manda
      para o bloco de mensagens em vez da tabela de campos alterados.
- [x] **O teto por hora desligava regra que não escrevia nada.** A contagem
      incluía as execuções que pararam na condição. Uma edição em massa de 200
      tarefas desligava justamente as regras de condição estreita — as bem
      escritas — por não terem feito nada.

## Dívidas conhecidas

- [x] A ação de **módulo** entrou, e a razão de ela ter ficado de fora estava
      errada: eu supus simetria com o ciclo. Não há. Um ciclo é sprint que
      termina, então id fixo envelhece; um módulo é contêiner durável
      ("Autenticação", "Relatórios"), e o id escolhido hoje continua certo em
      seis meses. Por isso ciclo resolve "o ativo agora" e módulo usa id fixo.
- [x] A simulação passou a mostrar **quando** é a próxima rodada, além de
      quantas tarefas casam. Calculado no servidor, pelo mesmo código do motor —
      refazer a conta em JavaScript daria duas respostas possíveis para a mesma
      pergunta, e o fuso é do projeto. Funciona sobre a regra ainda não salva,
      que é quando a pergunta importa.

- [x] O detalhe de `set_assignees` e `set_labels` passou a mostrar **nomes**.
      Contagem responde "quantas"; a pergunta de quem lê o registro é "quais".
- [x] `RECEITAS_DE_AUTOMACAO` ganhou consumidor na F3.7 — o item estava
      desatualizado desde que a tela de receitas foi ao ar.

## Fora de escopo até haver produção real

**Entrega de e-mail.** Decidido em 17/08/2026 pelo dono do produto: só quando
houver produção de verdade.

O que está medido, para não ser redescoberto:

|                          |                                                    |
| ------------------------ | -------------------------------------------------- |
| `EMAIL_HOST` no ambiente | `localhost` — nada escuta na porta 25 do contêiner |
| Fila pendente            | 49                                                 |
| Já enviados              | 0                                                  |

O código da ação `notify` está pronto e a fila enche normalmente — falta só um
SMTP configurado. **Não abra defeito por isto**: o e-mail não sai por decisão,
e não por regressão.

Dois efeitos colaterais **já resolvidos** em 18/08/2026, porque nenhum dependia
de produção real:

- a caixa "notificar por e-mail" vinha marcada por padrão e prometia um envio
  que não acontecia. Passou a seguir `is_smtp_configured`, que a API já expõe:
  sem SMTP nasce desmarcada e a tela diz por quê, e **no dia em que houver SMTP
  ela volta a nascer marcada sozinha**, sem tocar em código;
- a fila crescia para sempre. A poda apagava registros por `sent_at <= corte`, e
  nulo não casa com `<=`: o que nunca saiu ficava eternamente. Passou a podar
  pela IDADE do registro, tenha saído ou não.

O que continua dependendo de produção real é só a **entrega**: provedor,
credenciais, SPF/DKIM e a conferência de que uma mensagem chega mesmo a uma
caixa.
