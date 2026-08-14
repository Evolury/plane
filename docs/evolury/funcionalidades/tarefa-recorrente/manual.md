# Tarefa recorrente — Referência de comportamento

Fonte para o manual do usuário e para o material de treinamento. Descreve **o
que acontece**, em linguagem de quem usa. O _porquê_ de cada decisão está no
[ADR 0010](../../decisoes/0010-tarefas-recorrentes.md); o desenho detalhado, na
[especificação](especificacao.md).

## Em uma frase

Uma tarefa comum vira molde de trabalho que se repete: ligue **Repetir** nela,
escolha a agenda, e o sistema cria uma cópia nova a cada período.

## Onde se ativa

Na **própria tarefa**, na seção **Repetir** do painel de propriedades — a
mesma que aparece ao abrir a tarefa em tela cheia ou na visualização rápida.

Ligado o interruptor, abre a agenda. Só o **administrador do projeto** liga,
edita e desliga; para os demais a seção aparece desabilitada.

Em **Configurações do projeto → Execução → Tarefas recorrentes** fica a lista
de tudo que se repete no projeto. Não se cria nada por lá: a página é o painel
de auditoria, com o resumo da agenda, as próximas datas e os controles.

## Os três papéis de uma tarefa

| Papel | Como identificar | O que a seção Repetir mostra |
| --- | --- | --- |
| **Origem** | selo de repetição ao lado do código (VAL-12) | o interruptor ligado, a agenda e as próximas datas |
| **Gerada** | nasceu sozinha, código próprio | "Gerada pela recorrência de VAL-12" — clicável, leva à origem |
| **Comum** | nenhum dos dois | o interruptor desligado |

**A tarefa gerada não pode ter recorrência própria**, e **subtarefa também
não** — nesses casos a seção nem oferece o interruptor.

## A agenda

| Frequência | O que se escolhe |
| --- | --- |
| Diária | a cada N dias |
| Semanal | a cada N semanas, em um ou vários dias da semana |
| Mensal | a cada N meses, no dia D, no **último dia do mês**, ou na 1ª/2ª/3ª/4ª/última ocorrência de um dia da semana |
| Anual | a cada N anos, em dia e mês |

Mais, em todas: **horário**, **data de início**, **término** (nunca, numa data,
ou após N ocorrências) e **antecedência**.

Pontos que costumam gerar dúvida:

- **Quinzenal tem duas leituras**, e as duas existem: _semanal a cada 2
  semanas_ ("de duas em duas terças") e _mensal nos dias 1 e 15_ (duas regras).
- **"Todo dia 31" nunca some.** Em fevereiro gera em 28, em abril em 30 — o dia
  encurta para o último do mês em vez de pular o mês.
- **A semana começa no domingo** e o horário é o de Brasília.
- A **pré-visualização** mostra as próximas datas enquanto se configura. É a
  forma de conferir uma regra complexa sem precisar decifrá-la.

## Quando a tarefa nasce

**Por agenda** (padrão): na data da série, independentemente de a anterior ter
sido concluída.

**Após a conclusão**: N dias depois de a anterior ser concluída. Nesse modo,
quem dispara a primeira ocorrência é a conclusão da **tarefa de origem**.
Concluir com atraso **empurra** a próxima, nunca pula um período.

**Antecedência** — quantos **dias e horas** antes do vencimento a tarefa é
criada. Dias servem para a véspera ("o relatório chega 3 dias antes"); horas,
para o preparo ("a pauta chega 2 horas antes da reunião"). Padrão zero.

A data de nascimento vira a **data de início** da tarefa, e a data da agenda, o
**vencimento**. Mensal no dia 5 com 3 dias de antecedência: nasce em 02/09, com
início 02/09 e vencimento 05/09.

> As horas vão até 23. A partir de 24, use dias.
> O sistema verifica as regras a cada 15 minutos, então "2 horas antes"
> significa, no pior caso, 1h45 antes.

## O que a tarefa gerada traz

| Vem da origem | Não vem |
| --- | --- |
| Nome, descrição, prioridade | Comentários e histórico |
| Responsáveis, etiquetas | Datas (são calculadas) |
| Estimativa, tipo de tarefa | Anexos |
| Subtarefas (um nível, sem data) | Ciclo, módulo e relações |

O critério: **o que descreve o trabalho** vem; **o que descreve aquela
execução** fica para trás.

**A etapa em que ela nasce** é escolhida na regra — por padrão, a etapa padrão
do projeto. Ela **nunca** nasce na etapa em que a anterior foi concluída.

**As subtarefas vêm abertas e sem data.** As datas próprias, quando fizerem
falta, são preenchidas à mão. Limite de 50 subtarefas por ocorrência.

## Responsáveis

| Situação na origem | O que a tarefa gerada recebe |
| --- | --- |
| Tem responsáveis | os mesmos |
| Nenhum responsável | o **responsável padrão do projeto**, se houver |
| Responsável que saiu do projeto | os demais; quem saiu é descartado |

Quem sai de um projeto continua atribuído nas tarefas antigas. Nas recorrentes
isso é tratado:

- as próximas ocorrências já **nascem sem essa pessoa**;
- o painel de Tarefas recorrentes **marca a regra** e oferece remover a
  atribuição da origem em um clique;
- ao **remover alguém do projeto**, a confirmação avisa em quantas recorrentes
  ele é responsável e permite **transferir para outra pessoa** na mesma tela.

Remover alguém **nunca é bloqueado** por causa de recorrência, e a geração
**nunca para** por falta de responsável.

## Evitando pilha de cópias

A opção **"Não criar enquanto a ocorrência anterior estiver aberta"** vem
ligada. Com ela:

- conta a série inteira — a origem e todas as ocorrências, não só a última;
- "aberta" significa fora dos grupos **concluído** e **cancelado**; cancelar
  libera, excluir também;
- **concluir a anterior antes de a próxima vencer** — mesmo horas antes — faz a
  ocorrência do período nascer na verificação seguinte, com a antecedência que
  restou;
- **deixar o vencimento passar** com a anterior aberta **pula aquele período**:
  a série segue na data seguinte, e concluir depois não traz de volta o que
  passou.

Desligada a opção, cada data gera sua tarefa, aberta ou não a anterior.

## O ciclo de vida da tarefa de origem

A origem é trabalho de verdade, não um molde parado: aparece no quadro, é
concluída normalmente e costuma ficar em Concluído.

| O que se faz com a origem | O que acontece com a recorrência |
| --- | --- |
| Concluir | segue; no modo "após a conclusão", dispara a próxima |
| Arquivar | **pausa** — retoma ao desarquivar |
| Excluir | a recorrência é excluída junto |
| Editar (nome, descrição, responsáveis, subtarefas) | vale para as **próximas** ocorrências |

**Editar a origem é como se muda o que a recorrência gera.** Não há um molde
separado para manter.

Excluir uma **tarefa gerada** não afeta a série.

## Como pausar ou encerrar

| Objetivo | Caminho |
| --- | --- |
| Parar por um tempo | **Pausar**, no cartão ou no painel — reversível |
| Encerrar de vez | desligar o interruptor **Repetir** na tarefa, ou a lixeira no painel |
| Encontrar a recorrência meses depois | Configurações → Tarefas recorrentes; ou abrir a ocorrência da semana e clicar no rastro, que leva à origem |

Encerrar apaga a agenda e **preserva as tarefas já geradas** — elas são
trabalho, não histórico da regra. A tarefa de origem também permanece, como
tarefa comum.

## Fora do escopo hoje

- Anexos não são copiados.
- Subtarefa de subtarefa não é copiada (um nível apenas).
- Não há como pular uma ocorrência específica sem mexer na série.
- Feriado e dia útil não são considerados: se a data cair em feriado, a tarefa
  nasce assim mesmo.
- Vencimento próprio de subtarefa (por exemplo, "2 dias antes da principal")
  ainda não existe — as datas são preenchidas à mão.
