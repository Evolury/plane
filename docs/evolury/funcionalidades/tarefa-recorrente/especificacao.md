# Tarefa recorrente — Especificação

- **Status:** aprovada (13/08/2026), revisada em 13/08/2026
- **Decisões estruturais:** [ADR 0010](../../decisoes/0010-tarefas-recorrentes.md)

## Objetivo

Configurar uma vez o trabalho que se repete, e receber a tarefa pronta na data
certa — sem que ninguém precise lembrar de criá-la.

## Onde mora

**A recorrência é ativada na própria tarefa**, numa seção "Repetir" que existe
em todo cartão. Ligado o interruptor, abre a agenda. Só **admin do projeto**
liga, edita e desliga; para os demais a seção aparece desabilitada.

Configurações do projeto → **Execução** → **Tarefas recorrentes** é a **lista**
das tarefas com recorrência ativa no projeto — sem botão de criar. Rota
`/[workspaceSlug]/settings/projects/[projectId]/recurring/`. É o painel de
auditoria: o que este projeto gera sozinho, com a agenda resumida, as próximas
datas, pausar/retomar e o link para a tarefa.

## A regra

Cada regra é uma **agenda** ligada a uma **tarefa de origem**. A tarefa é o
molde, vivo: editá-la muda as próximas ocorrências.

### Agenda

| Frequência | O que se configura                                                    |
| ---------- | --------------------------------------------------------------------- |
| Diária     | a cada N dias                                                         |
| Semanal    | a cada N semanas, em um ou mais dias da semana                        |
| Mensal     | a cada N meses, no dia D **ou** na 1ª/2ª/3ª/4ª/última <dia da semana> |
| Anual      | a cada N anos, em dia e mês                                           |

Mais, em todas: **horário** da geração, **data de início**, **fim** (nunca, numa
data, ou após N ocorrências) e **antecedência**.

**Antecedência**: quanto antes do vencimento a tarefa é criada, em **dias e
horas**. Dias resolvem a véspera — o relatório que chega 3 dias antes; horas
resolvem o preparo — a pauta que chega 2 horas antes da reunião. Padrão zero
(nasce na hora). A data de nascimento vira a **data de início** da tarefa —
mensal no dia 5 com 3 dias de antecedência gera, em setembro, uma tarefa criada
em 02/09, com início 02/09 e vencimento 05/09. Horas valem até 23: a partir de
24, usa-se dias — "26 horas" e "1 dia e 2 horas" não podem ser duas regras
diferentes. No modo após a conclusão, a antecedência é limitada ao momento da
conclusão: não dá para nascer antes do gatilho existir.

A pré-visualização mostra as duas datas: _"nasce em 02/09 · vence em 05/09"_.
Quando a antecedência for maior ou igual ao intervalo, a tela **avisa** que as
ocorrências vão se sobrepor de forma permanente — sem bloquear.

Quinzenal sai de duas formas, porque a palavra tem duas leituras: _semanal com
intervalo 2_ ("de duas em duas semanas, na terça") e _mensal nos dias 1 e 15_.

**Dia que não existe no mês vira o último dia do mês.** "Todo dia 31" gera em
28/02, 30/04, 30/06, 30/09 e 30/11. A RFC 5545 manda ignorar a data inválida —
correto para calendário, errado para tarefa (ADR 0010).

**Fuso**: `America/Sao_Paulo`, o fuso do produto (ADR 0006). "Toda segunda às
8h" só significa alguma coisa com fuso definido.

**Semana**: começa no domingo (ADR 0005).

### Modo de geração

- **Por agenda** (padrão): a próxima data sai do calendário.
- **Após a conclusão**: a próxima data conta N dias a partir da conclusão da
  ocorrência anterior. Enquanto ninguém concluir, nada é gerado.

### Guarda contra acúmulo

**"Não criar enquanto a ocorrência anterior estiver aberta"**, ligada por
padrão. Desligada, cada data gera sua tarefa, aberta ou não a anterior.

Os critérios, com precisão:

- **Aberta** = etapa fora dos grupos concluído e cancelado. Cancelar libera a
  guarda; excluir também — tarefa excluída não segura nada, porque ninguém a
  vê no quadro para entender o bloqueio.
- **A série inteira conta**: a origem e todas as ocorrências, não só a última.
  A pilha de cópias começa na esquecida de três semanas atrás.
- **O ponto de virada é o vencimento, não o disparo.** Concluída a anterior
  antes de a próxima vencer — mesmo horas antes —, a ocorrência do período
  nasce na rodada seguinte do job (≤15 min), com a antecedência que restou.
  Vencimento passado com a anterior aberta, o período é **pulado**: o relógio
  desliza para a data seguinte, e concluir depois não ressuscita o que
  passou — despejar no quadro uma tarefa que já nasce vencida não ajuda
  ninguém (é a regra "atraso não acumula" aplicada à guarda).

### O que a ocorrência herda da origem

| Copia                       | Não copia                                     |
| --------------------------- | --------------------------------------------- |
| Nome, descrição, prioridade | Comentários e atividade                       |
| Responsáveis, etiquetas     | Datas de início e vencimento (são calculadas) |
| Estimativa, tipo de tarefa  | Anexos                                        |
|                             | Ciclo e módulo                                |
|                             | Relações e subtarefas                         |

_O que descreve o trabalho_ copia; _o que descreve aquela execução_ não.

**Etapa inicial**: a ocorrência nasce na etapa configurada na regra (padrão: a
etapa padrão do projeto), **nunca** na etapa em que a anterior foi concluída.

### A tarefa de origem

É trabalho real, não molde parado: pode ser concluída normalmente, e no modo
após a conclusão é ela quem dispara a próxima.

| Acontece com a origem | A regra                                          |
| --------------------- | ------------------------------------------------ |
| Concluída             | segue; no modo após conclusão, dispara a próxima |
| Arquivada             | pausa (retomável)                                |
| Excluída              | é excluída junto                                 |

**A tarefa gerada não pode ativar recorrência**: a seção aparece bloqueada,
dizendo "gerada pela recorrência de VAL-12". Sem a trava, a série viraria árvore.

### Responsável que sai do projeto

Remover alguém de um projeto não desfaz as atribuições dele — some dos
seletores, continua atribuído no que já tinha, inclusive na tarefa de origem.
Sem tratamento, toda ocorrência futura nasceria com um dono que não existe mais.

**A remoção nunca é travada** e **a geração nunca para**. O que acontece:

| Camada            | Comportamento                                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------------------------- |
| Geração           | descarta o responsável inativo; a ocorrência nasce sem ele, nunca com um fantasma                               |
| Configurações     | contador no item "Tarefas recorrentes" e linha marcada, com o conserto ali — só para admin do projeto           |
| Remoção do membro | a confirmação avisa quantas recorrentes ficam afetadas e oferece **transferir** para outra pessoa na mesma tela |

Trabalho com aparência de dono é pior que trabalho sem dono: ninguém assume o
que já parece atribuído. E tarefa sem responsável é auto-evidente no quadro —
tarefa que deixou de nascer, não ([ADR 0010](../../decisoes/0010-tarefas-recorrentes.md)).

**Origem sem responsável nenhum** gera ocorrência sem responsável, e **não**
dispara alerta: ausência é escolha legítima, e avisar sobre o normal gasta o
crédito do aviso. Nesse caso vale o **responsável padrão do projeto**, com a
mesma validação do caminho normal de criação (membro ativo, papel de membro ou
admin). Ele é rede de segurança, não sobreposição: nunca troca um responsável
de verdade, e só alcança a tarefa principal — subtarefa sem responsável é
normal, e carimbar todas com a mesma pessoa seria ruído.

As duas regras se completam: descartado o fantasma, se não sobrar ninguém, o
padrão do projeto assume.

### Subtarefas

As subtarefas da origem são copiadas — descrevem o trabalho, não a execução.
Vêm **abertas, sem comentários, sem atividade e sem data**. O reset não é
recurso: é consequência de copiar, como no ClickUp.

**Sem data é o padrão, e é decisão.** O defeito conhecido do Asana é a subtarefa
que nasce com a data do ciclo anterior, vencida desde o primeiro segundo. Uma
subtarefa sem data já comunica "vence com a principal", que é o caso comum.

**Quando o prazo importa, a subtarefa declara o próprio vencimento**:

| Âncora              | Exemplo        | Cálculo                      |
| ------------------- | -------------- | ---------------------------- |
| Após o nascimento   | "1 dia depois" | início da ocorrência + N     |
| Antes do vencimento | "2 dias antes" | vencimento da ocorrência − N |
| Sem regra (padrão)  | —              | sem data                     |

O deslocamento é sempre positivo: a direção vem da âncora, não do sinal. E a
data é calculada **a cada ciclo, do zero** — nunca deslocada de um ciclo para o
outro, que é onde o remapeamento do ClickUp falha quando a data do pai recua.

**Nunca antes do nascimento**: deslocamento maior que a janela é recortado no
dia em que a ocorrência nasce. Data ausente não mente, e data impossível
também não pode.

O campo aparece na linha da subtarefa, só nas subtarefas de uma tarefa de
origem, e só para admin.

Três travas:

- **Subtarefa não tem recorrência própria.** Principal recorrendo mais subtarefa
  recorrendo é o que produz a duplicação em cascata relatada no Asana.
- **Um nível só.** Subtarefa de subtarefa não é copiada.
- **Teto de 50 subtarefas por ocorrência**, com aviso ao configurar. Acima disso
  a ocorrência é um projeto disfarçado. O ClickUp corta em 500 e **remove a
  recorrência da tarefa** ao passar do teto — aqui o aviso vem antes, e a regra
  de ninguém é apagada em silêncio.

A guarda de ocorrência aberta continua lendo a tarefa principal: a confirmação
de subtarefas abertas ([ADR 0009](../../decisoes/0009-botao-concluir-tarefa.md))
já obriga a decidir sobre elas no momento de concluir.

## O que acontece na hora

Um job roda a cada 15 minutos e, para cada regra vencida:

1. confere a guarda (anterior aberta?) e o fim da recorrência;
2. copia a tarefa de origem, na etapa inicial da regra;
3. grava as datas: início = hoje, vencimento = a data da ocorrência;
4. registra a ocorrência (data prevista → tarefa criada);
5. recalcula a próxima data.

Com antecedência N, a regra vence N dias antes da data da ocorrência — é o
mesmo job, com o relógio adiantado.

**Atraso não acumula**: se o job ficou fora do ar, gera **uma** ocorrência — a
mais recente devida — e segue. O registro de ocorrências garante que rodar duas
vezes não cria duas tarefas para a mesma data.

## A tarefa gerada

É uma tarefa comum, com uma origem: aparece em "Minhas tarefas" na etapa padrão
de cada responsável, pode ser concluída pelo botão, e gera atividade, webhook e
notificação — com **o autor da regra como ator**.

**Nasce fora de ciclo e de módulo**, porque ciclo e módulo descrevem aquela
execução, não o trabalho. Adicionada a um ciclo à mão, conta nos gráficos como
qualquer outra — o que não acontece é herdar o ciclo da origem, que estaria
encerrado quando a ocorrência nasce.

**Não passa por triagem**, mesmo com a entrada ativada: trabalho agendado por um
admin já está aprovado.

A automação de arquivar e fechar alcança ocorrências antigas concluídas, como
alcança qualquer tarefa. É a limpeza do histórico.

## Fora de escopo (v1)

| Item                             | Por quê                                             |
| -------------------------------- | --------------------------------------------------- |
| Anexos na cópia                  | custo de storage por ocorrência                     |
| Vencimento relativo da subtarefa | adição pura, sem migração; a fase já carrega uma    |
| Subtarefa aninhada               | multiplica o custo da geração                       |
| Pular uma ocorrência             | o registro de ocorrências já deixa pronto o terreno |
| Feriado e dia útil               | exige calendário de feriados                        |

## Perguntas resolvidas

**Por que não criar todas as ocorrências futuras de uma vez?** Encheria o
projeto de tarefas que ainda não existem, e faria de qualquer edição da regra
uma migração. Quem precisa **enxergar** o futuro tem a pré-visualização; a
antecedência é para quem precisa **trabalhar** antes.

**Por que a ocorrência é uma cópia, e não a mesma tarefa reaproveitada?**
Porque cada ciclo tem histórico próprio, e porque reaproveitar exigiria desfazer
a conclusão toda vez — atividade falsa, métrica errada, tarefa saltando de
Concluído para A fazer. O modelo de tarefa única (Todoist) só funciona onde não
há etapa nem histórico a preservar.

**E o risco de concluir a cópia por engano, como acontece no Asana?** Lá a nova
instância nasce na seção de onde a anterior foi concluída, no instante do
clique, e o cartão não mostra ID nem selo — três coisas que aqui não acontecem:
a ocorrência nasce na etapa inicial, nasce na data dela (ou N dias antes), e
carrega ID próprio mais o selo de origem.

**E se o responsável sair do projeto?** A ocorrência é criada sem ele; a regra
continua válida. Vale um aviso na tela de configuração — anotado para a F2.
