# Tarefa recorrente — Especificação

- **Status:** aprovada (13/08/2026)
- **Decisões estruturais:** [ADR 0010](../../decisoes/0010-tarefas-recorrentes.md)

## Objetivo

Configurar uma vez o trabalho que se repete, e receber a tarefa pronta na data
certa — sem que ninguém precise lembrar de criá-la.

## Onde mora

Configurações do projeto → **Execução** → **Tarefas recorrentes**, ao lado das
Automações. Rota `/[workspaceSlug]/settings/projects/[projectId]/recurring/`.
Só **admin do projeto** cria, edita e exclui; membro e convidado não veem o
item.

## A regra

Cada regra tem um nome (o da tarefa que será criada), uma **agenda** e um
**molde**.

### Agenda

| Frequência | O que se configura |
| --- | --- |
| Diária | a cada N dias |
| Semanal | a cada N semanas, em um ou mais dias da semana |
| Mensal | a cada N meses, no dia D **ou** na 1ª/2ª/3ª/4ª/última <dia da semana> |
| Anual | a cada N anos, em dia e mês |

Mais, em todas: **horário** da geração, **data de início** e **fim** (nunca,
numa data, ou após N ocorrências).

Quinzenal sai de duas formas, porque a palavra tem duas leituras: *semanal com
intervalo 2* ("de duas em duas semanas, na terça") e *mensal nos dias 1 e 15*.

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

### Molde

Nome, descrição, prioridade, estado inicial, responsáveis, etiquetas,
estimativa e tipo de tarefa.

Fora do v1: **anexos** (custo de storage por ocorrência) e **subtarefas**
(planejadas para o ciclo seguinte).

## O que acontece na hora

Um job roda a cada 15 minutos e, para cada regra vencida:

1. confere a guarda (anterior aberta?) e o fim da recorrência;
2. cria a tarefa a partir do molde, no projeto da regra;
3. registra a ocorrência (data prevista → tarefa criada);
4. recalcula a próxima data.

**Atraso não acumula**: se o job ficou fora do ar, gera **uma** ocorrência — a
mais recente devida — e segue. O registro de ocorrências garante que rodar duas
vezes não cria duas tarefas para a mesma data.

## A tarefa gerada

É uma tarefa comum, com uma origem: conta em ciclo e módulo, aparece em "Minhas
tarefas" na etapa padrão de cada responsável, pode ser concluída pelo botão, e
gera atividade, webhook e notificação — com **o autor da regra como ator**.

**Não passa por triagem**, mesmo com a entrada ativada: trabalho agendado por um
admin já está aprovado.

A automação de arquivar e fechar alcança ocorrências antigas concluídas, como
alcança qualquer tarefa. É a limpeza do histórico.

## Fora de escopo (v1)

| Item | Por quê |
| --- | --- |
| Subtarefas no molde | maior fonte de defeito conhecida do Asana; ciclo próprio, logo após esta entrega |
| Anexos no molde | custo de storage por ocorrência |
| "Tornar esta tarefa recorrente" | porta de entrada, entra na F3 |
| Pular uma ocorrência | o registro de ocorrências já deixa pronto o terreno |
| Feriado e dia útil | exige calendário de feriados |

## Perguntas resolvidas

**Por que não criar todas as ocorrências futuras de uma vez?** Encheria o
projeto de tarefas que ainda não existem, e faria de qualquer edição da regra
uma migração.

**Por que a regra não vive na tarefa, como no Asana?** Porque aí não há onde
listar e auditar o que está agendado. A porta de entrada pela tarefa vem na F3,
gravando na mesma tabela.

**E se o responsável sair do projeto?** A ocorrência é criada sem ele; a regra
continua válida. Vale um aviso na tela de configuração — anotado para a F2.
