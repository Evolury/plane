# ADR 0010 — Tarefas recorrentes

- **Status:** Aceito (13/08/2026)
- **Contexto:** funcionalidade [tarefa-recorrente](../funcionalidades/tarefa-recorrente/especificacao.md)
- **Relacionado:** [ADR 0005](0005-semana-comeca-no-domingo.md) (semana), [ADR 0006](0006-fusos-do-brasil.md) (fuso), [ADR 0009](0009-botao-concluir-tarefa.md) (conclusão)

## Contexto

O produto precisa de trabalho que se repete: o relatório de toda segunda, a
revisão do dia 1º, o backup de quinze em quinze dias. Hoje isso vira tarefa
criada à mão, ou não vira nada.

O levantamento no código mostrou três fatos que moldam a decisão:

1. **As chaves de tradução já existem** (`recurring_work_items.*`), órfãs, vindas
   da edição paga. Elas revelam o desenho do upstream: página de configurações,
   formulário com "Agendamento", e um empty state que fala em `no_templates` —
   lá a recorrência é _template + agenda_.
2. **Templates não existem nesta edição.** Não há modelo nem endpoint. A regra
   precisa carregar o próprio molde.
3. **A infraestrutura de agendamento está pronta**: Celery beat com
   `DatabaseScheduler` e jobs periódicos em produção. E `dateutil.rrule`, que
   implementa a RFC 5545, já está na imagem — por transitividade, o que não
   basta (ver Consequências).

## Decisão

**A regra mora nas configurações do projeto, em Execução**, ao lado das
Automações, e é criada por **admin do projeto**. Cada regra é um par
_agenda + molde_: quando gerar, e o que gerar.

### A agenda

Guardada em **campos legíveis** — frequência, intervalo, dias da semana,
horário — e traduzida para `rrule` na hora de calcular. Guardar RRULE cru
economizaria código e custaria a tela: ninguém edita
`FREQ=MONTHLY;BYSETPOS=-1;BYDAY=FR` num formulário.

Frequências: **diária**, **semanal** (com escolha de dias), **mensal** (dia do
mês ou "primeira/última <dia da semana>") e **anual**, todas com intervalo — o
que dá quinzenal nas duas leituras que a palavra tem: _a cada 2 semanas_ e
_nos dias 1 e 15_.

**Dia que não existe no mês vira o último dia do mês.** A RFC 5545 manda
ignorar a data inválida, então `BYMONTHDAY=31` simplesmente **pula** fevereiro,
abril, junho, setembro e novembro. É o comportamento correto para calendário e
errado para tarefa: quem pede "todo dia 31" quer dizer "todo fim de mês", e um
silêncio de cinco meses por ano seria um bug que ninguém relaciona à causa.

### A geração

Um job periódico cria as ocorrências. Duas escolhas o definem:

- **Por agenda** (padrão): a próxima data sai do calendário, independentemente
  de conclusão.
- **Após a conclusão**: a próxima data conta a partir da conclusão da anterior.
  É o vocabulário do Todoist (`every!`), e resolve "revisar 15 dias depois da
  última revisão", que por agenda fica errado quando alguém atrasa.

**Ocorrência atrasada não acumula.** Se o job ficou fora do ar, a rodada seguinte
gera **uma** ocorrência — a mais recente devida — e segue. Criar retroativamente
tudo que se perdeu enche o quadro de trabalho que ninguém vai fazer.

**Enquanto a anterior estiver aberta, não gera** (ligado por padrão). É a
resposta ao problema número um de recorrência em ferramenta de trabalho: o
quadro entupido de cópias da mesma coisa. Quem quiser o contrário desliga.

### O molde

> Substituído pela revisão de 13/08/2026: o molde deixou de ser campo da regra
> e passou a ser a tarefa de origem. A lista de campos abaixo continua valendo —
> mudou de onde eles vêm. E as subtarefas entram, sem data (ver adiante).

Nome, descrição, prioridade, estado inicial, responsáveis, etiquetas,
estimativa e tipo de tarefa. **Sem anexos** (custo de storage por ocorrência) e
**sem subtarefas** no v1 — subtarefa em recorrência é a maior fonte de defeito
conhecida do Asana, com relatos de duplicação, sumiço e volta marcada como
concluída. Entra depois, com regra própria.

**A ocorrência não passa por triagem.** Trabalho agendado por um admin já está
aprovado; mandá-lo para a fila de entrada seria pedir aprovação de novo.

**O ator das atividades é quem criou a regra.** Toda ocorrência gera atividade,
webhook e notificação como qualquer tarefa — e atividade sem ator é buraco no
histórico.

### Conferido contra o Asana (13/08/2026)

As regras mensais foram validadas contra a referência do pedido. O Asana tem
"último dia do mês" como **opção própria**, e não como "dia 31" — e faz sentido:
ninguém pensa "dia 31" quando quer dizer "fecha o mês". Aqui ela virou o modo
`last_day`, que internamente é o dia 31 com o encurtamento que já existia.

Ele também tem o n-ésimo dia da semana, que já tínhamos, com uma diferença a
nosso favor: os relatos do fórum mostram gente pedindo a **última** semana, que
nós já oferecemos desde o começo.

E há um defeito conhecido lá que vale citar porque desenha a nossa regra: com
recorrência dirigida pela conclusão, **concluir com atraso pula um período
inteiro** — tarefa do dia 31 de maio concluída em 3 de junho reaparece em
julho, sem passar por junho. Aqui isso não acontece por construção: no modo por
agenda as datas saem da série, não da conclusão; e no modo após a conclusão a
data nova conta a partir do momento em que a pessoa terminou, então atrasar
**empurra** a próxima em vez de sumir com ela. Há teste para os dois casos.

### Revisão de 13/08/2026 — a recorrência mora na tarefa

O molde separado errou. Pedir os dados da tarefa num formulário paralelo, dentro
das configurações, obriga a pessoa a descrever de novo o que ela já sabe
descrever — e cria duas verdades sobre a mesma coisa, que divergem no primeiro
dia em que alguém edita uma e esquece a outra.

**A regra passa a apontar para uma tarefa** (`source_issue`). A tarefa _é_ o
molde, vivo: editá-la muda as próximas ocorrências, sem sincronização. É como
Asana, ClickUp e Todoist fazem, e nenhum deles tem formulário paralelo.

**A seção "Repetir" fica na própria tarefa**, ligada por um interruptor. Fora do
calendário, porque a data de vencimento responde "quando esta" e a recorrência
responde "quando as próximas" — são perguntas diferentes.

**A página de configurações perde o botão de criar** e vira a lista das tarefas
com recorrência ativa. O argumento que fez a regra nascer nas configurações
— _precisa haver onde auditar o que está agendado_ — continua de pé; ele só não
exigia que a criação também morasse lá. É justamente o que falta no Asana, onde
a recorrência é invisível fora da tarefa.

**O que a ocorrência copia**: nome, descrição, prioridade, responsáveis,
etiquetas, estimativa e tipo. **O que não copia**: comentários, atividade,
anexos, ciclo, módulo e relações. O critério é _o que descreve o trabalho_ copia,
_o que descreve aquela execução_ não.

**As datas não são copiadas — são calculadas** (ver antecedência, abaixo).

**A tarefa gerada não pode ativar recorrência.** Sem a trava, concluir uma
ocorrência recorrente geraria uma neta, e a série viraria uma árvore. A trava
também entrega o rastro de graça: a seção bloqueada diz "gerada pela recorrência
de VAL-12", que era o item F3.1.

**A origem é trabalho real**, não um molde parado: é concluída normalmente, e no
modo após a conclusão é ela quem dispara a próxima. **Arquivar a origem pausa a
regra** — uma tarefa fora do quadro não deve continuar gerando trabalho, mas
arquivar não é decisão sobre o futuro, e pausar se desfaz. **Excluir apaga.**

### A ocorrência nasce onde e quando

Duas decisões que parecem detalhe de interface e são de modelo.

**Nasce na etapa inicial da regra** (padrão: a etapa padrão do projeto), nunca na
etapa em que a anterior foi concluída. É o defeito mais reclamado do Asana, onde
a nova instância _"reaparece somente na seção de onde foi concluída"_ — some
dentro da coluna Concluído e é reconcluída por engano. O ClickUp devolve ao
primeiro status; o monday deixa escolher, e é o que adotamos.

**Nasce com antecedência configurável** — dias e horas antes do vencimento, e
essa data de nascimento vira a **data de início** da tarefa. Uma regra mensal no
dia 5 com 3 dias de antecedência gera, em setembro, uma tarefa criada em 02/09,
com início 02/09 e vencimento 05/09. As horas cobrem o preparo dentro do dia —
a pauta que chega 2 horas antes da reunião — e valem até 23: a partir de 24,
usa-se dias, para "26 horas" e "1 dia e 2 horas" não serem duas regras
diferentes.

Sem isso a tarefa apareceria no dia em que já vence, o que atrapalha quem
planeja. O modelo é o do ClickUp, onde _"a data de início sempre recorre o mesmo
número de dias antes do vencimento"_ — a antecedência não é um campo à parte, é
a distância entre início e vencimento que a série preserva. O Wrike resolve o
mesmo problema por quantidade ("quantas tarefas quer ter no ar ao mesmo tempo");
medir em dias é mais direto quando existe vencimento.

O padrão é zero, que é o comportamento de hoje. Não há número universal: no
fórum do Asana convivem o pedido de ver antes e o pedido de [não ver até o
vencimento](https://forum.asana.com/t/dont-show-recurring-tasks-until-due-date/77051)
— por isso é configuração, não constante.

Antecedência grande faz a próxima nascer antes de a anterior fechar, e a guarda
de ocorrência aberta deixa de ser detalhe para virar o par natural dela. Quando
a antecedência for **maior ou igual ao intervalo**, a sobreposição é permanente:
avisar na tela, sem bloquear — pode ser intencional numa esteira contínua, mas
ninguém deveria cair nisso sem perceber.

### Subtarefas, sem data

Elas entram na cópia — descrevem o trabalho — e vêm **sem data nenhuma**.

O defeito do Asana não é copiar subtarefa, é copiá-la com a data do ciclo
anterior: _"todas as subtarefas mantêm as datas da tarefa que acabou de ser
concluída"_, vencidas no primeiro segundo de vida. Data ausente não mente; data
errada mente. E uma subtarefa sem data já comunica "vence com a principal", que
é o caso comum.

O vencimento relativo — âncora na criação ou no vencimento da principal, como o
remapeamento do ClickUp, só que declarado em vez de deduzido — ficou para o
ciclo seguinte, e **entrou em 14/08/2026** (ver adiante). Foi adição pura: quem
não configurar continua sem data.

Três travas nascem com a cópia: **subtarefa não tem recorrência própria** (é o
que produz a duplicação em cascata do Asana, 6 virando 12), **um nível só**, e
**teto de 50 por ocorrência**. O ClickUp corta em 500 e remove a recorrência da
tarefa ao passar — aqui o aviso vem antes, e a regra de ninguém some em silêncio.

O reset das subtarefas não precisa de interruptor como no Todoist: copiar já
entrega tudo aberto.

### Responsável que sai do projeto

Remover alguém de um projeto **não desfaz as atribuições**: o `destroy` só marca
`is_active = False` no vínculo, e as linhas de `IssueAssignee` sobrevivem. A
pessoa some dos seletores e continua atribuída no que já tinha — inclusive na
tarefa de origem, de onde a cópia puxa os responsáveis.

Numa tarefa comum isso é uma linha velha que alguém corrige. Numa recorrência é
uma **fábrica de atribuições erradas**: toda ocorrência nasce com dono que não
existe mais, e trabalho com aparência de dono é pior que trabalho sem dono —
ninguém assume o que já parece atribuído.

**Não travamos a remoção.** Tirar alguém de um projeto é ato de governança —
desligamento, fim de contrato, incidente — e precisa acontecer na hora. Travar
punia o momento errado (quem remove raramente é dono das recorrências) e criava
incentivo perverso: a saída mais rápida do bloqueio seria _excluir a
recorrência_, destruindo sob pressão a configuração que deveria ser transferida.
Ninguém no mercado trava — GitHub, Google e Atlassian removem primeiro e
mostram o que ficou órfão depois.

**Nem pausamos a regra.** É onde deixamos de copiar o Asana de propósito: lá a
automação pausa porque, sem a propriedade, ela não tem o que fazer — a falha é
total. Aqui é parcial: a agenda continua sabendo o que gerar, só perdeu um
responsável. Pausar jogaria fora o trabalho inteiro por causa de um atributo, e
produziria o silêncio contra o qual esta funcionalidade inteira foi desenhada.
Um backup semanal que deixa de nascer porque alguém saiu da empresa é muito pior
que um backup que nasce sem dono: tarefa sem responsável é auto-evidente no
quadro; tarefa que não existe, não.

Três camadas, cada uma cobrindo o que a outra deixa passar:

1. **A geração descarta o inativo** — a ocorrência nasce sem ele, nunca com um
   fantasma, e nunca deixa de nascer.
2. **O alerta persiste onde o conserto acontece**: contador no item "Tarefas
   recorrentes" das configurações, linha marcada, conserto ali mesmo. Só para
   **admin do projeto** — alerta que quem vê não pode resolver é ruído, e ruído
   ensina todo mundo a ignorar alerta, inclusive o legítimo.
3. **O aviso no instante da remoção**, com transferência para outra pessoa na
   mesma tela. É o gesto único de offboarding do Atlassian e do Google: remover
   e transferir juntos. A remoção acontece de qualquer forma; o que muda é
   deixar de ser silenciosa.

A regra que as três expressam: **o ato administrativo nunca é bloqueado, a
consequência dele nunca é silenciosa, e o trabalho nunca deixa de acontecer por
causa de metadado.**

**Origem sem responsável nenhum não é o mesmo caso.** A ocorrência nasce sem
responsável, e **nenhum alerta dispara**: ausência é escolha legítima — muita
equipe trabalha por puxada —, enquanto o fantasma é degradação silenciosa de
algo que alguém configurou. Alertar sobre o normal imporia um jeito de
trabalhar e gastaria o crédito do aviso: quem recebe alerta de coisa comum
para de ler alerta.

O que vale nesse caso é o **responsável padrão do projeto**, que o produto já
aplica em toda tarefa criada sem responsável — com validação de membro ativo e
papel de membro ou admin. A geração criava a tarefa direto no banco e ignorava
esse padrão, o que deixava a regra do projeto valendo em tudo **menos nas
tarefas que nascem sozinhas** — justamente as que ninguém está olhando no
momento em que nascem. Agora a geração o honra, com a mesma validação, e
apenas na tarefa principal: subtarefa sem responsável é normal, e carimbar
todas com a mesma pessoa seria ruído.

As duas regras se completam: descartado o fantasma, se não sobrar ninguém, o
padrão do projeto assume.

### Vencimento relativo da subtarefa (14/08/2026)

Uma recorrente semanal com três subtarefas datadas custa 156 preenchimentos de
data por ano — exatamente a repetição que a funcionalidade existe para
eliminar. E subtarefa sem data não aparece no calendário nem no cronograma, e
não dispara aviso: o trabalho miúdo fica escondido dentro do cartão.

Cada subtarefa da origem pode declarar **âncora + deslocamento**: "1 dia após o
nascimento" ou "2 dias antes do vencimento" da ocorrência. Sempre positivo — a
direção vem da âncora, não do sinal, porque número negativo em campo de prazo é
onde a interface confunde. Sem declaração, a subtarefa continua nascendo sem
data, que é o padrão e uma escolha legítima.

**O nosso problema é de criação, não de mutação**, e é isso que nos livra da
classe de defeito do mercado. O ClickUp precisa decidir como deslocar datas que
já existem quando o pai muda — daí o remapeamento que [não funciona quando a
data recua](https://feedback.clickup.com/feature-requests/p/reschedule-subtasks-when-parent-task-moved-to-an-earlier-date),
que ignora subtarefa sem data, e que não dispara pelo Gantt. Aqui não há data
anterior para deslocar: a cada ciclo a data é calculada do zero.

O Asana é o buraco mais claro: os modelos só oferecem "X dias após a criação", e
"N dias antes do vencimento do pai" é pedido recorrente no fórum, sem resposta.

**A regra de segurança**: se o cálculo cair antes do nascimento da ocorrência, a
data vira o próprio nascimento. Data ausente não mente, e data impossível
também não pode. Subtarefa que nasce vencida é o defeito do Asana que a revisão
evitou não copiando datas — seria irônico reintroduzi-lo pela porta da frente.

A agenda mora em **tabela própria**, e não em colunas de `issues`: é recurso de
nicho e `issues` é a maior tabela do banco. A cascata dos dois lados faz a
limpeza sozinha, e subtarefa nova simplesmente não tem linha.

## Alternativas consideradas

- **Guardar RRULE cru**: menos código, tela impossível. Descartado.
- **Recorrência como propriedade da tarefa** (modelo do Asana, onde a tarefa
  "se repete"): descartado na decisão original por não dar lugar de auditoria —
  **revertido na revisão acima**, ao perceber que auditar exige uma lista, não um
  formulário. A lista ficou; a criação voltou para a tarefa.
- **Reaproveitar a mesma tarefa a cada ciclo**, avançando o vencimento (modelo
  do Todoist, onde a recorrente nunca vai para a lista de concluídas): elegante
  para lista pessoal, destrutivo aqui. Concluir teria de ser desfeito toda vez,
  a tarefa saltaria de Concluído para A fazer gerando atividade falsa, e o ano
  inteiro contaria como uma conclusão só nas métricas. Descartado.
- **Criar todas as ocorrências futuras de uma vez** (como alguns calendários):
  previsível, mas enche o projeto de tarefas que ainda não existem e torna
  qualquer edição da regra uma migração. Descartado.

## Consequências

- **`python-dateutil` passa a ser dependência declarada da API.** Ele já está
  na imagem por transitividade, e foi exatamente assim que o `live` caiu em
  13/08/2026 — dependência que sobrevive por sorte some quando o grafo muda.
- Cada ocorrência é uma tarefa comum: conta em ciclo e módulo, aparece em
  "Minhas tarefas" na etapa padrão de cada responsável, e pode ser concluída
  pelo botão como qualquer outra.
  > Precisado em 14/08/2026, ao executar a matriz de compatibilidade: a
  > ocorrência **nasce fora** de ciclo e módulo — a revisão tirou os dois da
  > cópia. Adicionada a um ciclo à mão, conta normalmente; o que não acontece é
  > herdar o ciclo da origem, que estaria encerrado quando ela nasce.
- A automação de arquivar e fechar vai alcançar ocorrências antigas concluídas.
  É desejável — é a limpeza do histórico — mas precisa estar escrito.
- O registro de ocorrências (qual data gerou qual tarefa) é o que garante
  idempotência sob repetição do job e o que vai permitir, depois, **pular uma
  ocorrência** sem mexer na série.
- Feriado e dia útil ficam de fora: exigem calendário de feriados, que é outro
  projeto.
- **A revisão exige migração de dados, não só de esquema.** Havia uma regra em
  produção quando ela foi escrita. Cada molde vira uma tarefa de verdade, que
  passa a ser a origem da sua regra — melhor do que promover a ocorrência já
  gerada, que violaria a trava logo na estreia. O motor, o cálculo de datas e as
  guardas não mudam: muda de onde vêm os dados do molde.
