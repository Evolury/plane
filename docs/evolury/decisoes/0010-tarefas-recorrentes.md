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
   lá a recorrência é *template + agenda*.
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
que dá quinzenal nas duas leituras que a palavra tem: *a cada 2 semanas* e
*nos dias 1 e 15*.

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

## Alternativas consideradas

- **Guardar RRULE cru**: menos código, tela impossível. Descartado.
- **Recorrência como propriedade da tarefa** (modelo do Asana, onde a tarefa
  "se repete"): casa com a intuição de quem usa, mas espalha a regra por todas
  as tarefas e não dá lugar para listar e auditar o que está agendado. Fica
  como **porta de entrada** na F3 ("tornar recorrente"), gravando na mesma
  tabela.
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
- A automação de arquivar e fechar vai alcançar ocorrências antigas concluídas.
  É desejável — é a limpeza do histórico — mas precisa estar escrito.
- O registro de ocorrências (qual data gerou qual tarefa) é o que garante
  idempotência sob repetição do job e o que vai permitir, depois, **pular uma
  ocorrência** sem mexer na série.
- Feriado e dia útil ficam de fora: exigem calendário de feriados, que é outro
  projeto.
