# ADR 0014 — Etapas de "Minhas tarefas" movidas pelo vencimento

- **Status:** Aceito (18/08/2026)
- **Contexto:** funcionalidade [minhas-tarefas](../funcionalidades/minhas-tarefas/especificacao.md)
- **Relacionado:** [ADR 0001](0001-minhas-tarefas-overlay-pessoal.md) (overlay pessoal), [ADR 0002](0002-agrupamento-por-etapa-fonte-aditiva.md) (agrupamento), [ADR 0006](0006-fusos-do-brasil.md) (fuso), [ADR 0012](0012-automacoes-personalizadas.md) (motor de automação), [ADR 0013](0013-atualizacao-em-tempo-real.md) (tempo real)

## Contexto

As etapas pessoais organizam o que é meu, mas quem as mantém organizadas sou eu.
Toda manhã a mesma faxina: puxar o que venceu, trazer o que é de hoje, empurrar
o que ficou para depois. É trabalho que o produto sabe fazer — a data está lá — e
que ele deixava para a pessoa.

O pedido: uma varredura diária que, virada a meia-noite, ponha cada tarefa na
etapa que o vencimento dela indica.

## A decisão em uma frase

**A etapa passa a ser a leitura visual do vencimento**, e o arrasto entre as duas
etapas de curto prazo passa a ser a forma de reagendar.

Isso é o que evita o conflito que mata funcionalidades assim: se a etapa fosse um
lugar independente da data, a pessoa arrastaria uma tarefa para "Em Andamento" e
a madrugada a puxaria de volta. Com a etapa significando a data, pessoa e
automação concordam por construção.

## As regras

Toda madrugada, no fuso de cada pessoa:

| Situação da tarefa  | Destino               |
| ------------------- | --------------------- |
| vencimento < hoje   | etapa de **vencidas** |
| vencimento = hoje   | etapa de **hoje**     |
| vencimento = amanhã | etapa de **amanhã**   |
| vencimento ≥ D+2    | etapa de **depois**   |
| **sem vencimento**  | etapa de **hoje**     |

### Por que tarefa sem data vai para hoje

Não é caso de borda mal resolvido: é conceito do produto. **Tarefa sem
vencimento é tarefa esquecida.** Mandá-la para hoje é pô-la na frente de quem
pode decidir — a pessoa vê, dá uma data e move para onde ela pertence.

E é por isso que **a automação nunca carimba data**. Se ela carimbasse "hoje" ao
mover, a tarefa esquecida viraria uma tarefa de hoje como outra qualquer, e o
lembrete se apagaria no mesmo gesto que o criou. A ausência da data é a mensagem.

## As duas marcações, e por que são diferentes uma da outra

O modelo já tinha duas marcações exclusivas por pessoa/workspace — `is_default`
(onde chega tarefa nova) e `is_completion` (onde vai a concluída), cada uma com
uma constraint parcial. As quatro novas seguem o mesmo molde, com uma diferença
que importa:

- **a etapa padrão é obrigatória** — o seed sempre cria uma, porque item sem
  associação precisa pertencer a algum lugar;
- **as quatro de vencimento são opcionais.** Balde sem etapa marcada
  simplesmente não move ninguém. Quem não quiser a separação por amanhã, não
  marca, e o produto para de opinar sobre aquilo.

A constraint que sustenta as duas é a mesma: ela impede **duas** etapas para o
mesmo papel, e não exige uma. Uma etapa pode acumular vários papéis — "Futuro"
sendo amanhã e depois ao mesmo tempo é escolha legítima.

## O opt-out é de SAÍDA, nunca de chegada

"Remover a automação desta etapa" significa **não tirar tarefa daqui**. Chegar
continua podendo, sempre.

Escrito assim porque a regra se implementa ao contrário com facilidade — e o
sintoma seria silencioso. A etapa de vencidas é o exemplo que prova: ela é
**destino** das vencidas e, ao mesmo tempo, a etapa que a pessoa mais quer
travar, porque põe ali coisa à mão que não quer ver saindo sozinha. Se o opt-out
bloqueasse a chegada, ela nunca receberia nada e ninguém entenderia por quê.

Consequência a declarar: uma tarefa vencida que a pessoa repactuar para semana
que vem **fica em vencidas até ela mesma tirar**. É o comportamento pedido, e é
o preço de a etapa poder ser um lugar de decisão humana.

## O arrasto que reagenda

- arrastar para a etapa de **hoje** → vencimento vira hoje;
- arrastar para a etapa de **amanhã** → vencimento vira amanhã;
- qualquer outro destino → a data não é tocada.

Só essas duas, e de propósito. "Depois" e "vencidas" não têm data que se deduza:
"depois" é um intervalo aberto e "vencidas" é passado, que ninguém quer escrever
numa tarefa. Carimbar ali seria inventar informação.

Este é o único caminho que escreve `target_date`, e ele é humano por definição —
o que significa que gera histórico, aciona regras do [ADR 0012](0012-automacoes-personalizadas.md)
e propaga pelo canal do [ADR 0013](0013-atualizacao-em-tempo-real.md), como
qualquer edição feita à mão.

## Travas estruturais

Fora do alcance da varredura, sem depender de a pessoa lembrar de marcar:

- **concluída e cancelada.** Uma tarefa concluída ontem está tecnicamente
  vencida, e movê-la para "vencidas" seria ressuscitar trabalho terminado. Fica
  na trava do motor, e não numa caixa que alguém precisa achar;
- **balde sem etapa marcada** não move ninguém;
- **etapa marcada como sem automação** não solta ninguém.

## O relógio

A virada acontece no fuso de **cada pessoa** (`User.user_timezone`, que já
existe e nasce em `America/Sao_Paulo`), e não no do servidor — etapa pessoal é
pessoal também no relógio.

Por isso a varredura roda de quinze em quinze minutos, e não uma vez por noite:
meia-noite não é um instante, é um instante por fuso. Mesma cadência e mesmo
motivo das [tarefas recorrentes](0010-tarefas-recorrentes.md) e das automações
agendadas.

Um marcador por pessoa/workspace registra o último dia varrido. Ele não existe
para evitar repetição — a varredura é idempotente e rodar duas vezes não muda
nada — e sim para **se recuperar sozinha**: worker fora do ar na hora da virada
não custa o dia inteiro de organização de ninguém.

## Alternativas consideradas

**Baldes como visão, e não como etapa.** Calcular "hoje/amanhã/depois" na
leitura, deixando as etapas intocadas — é o que Todoist e Things fazem. Descartada
porque aqui a etapa **é** o quadro: a pessoa arrasta, e o arrasto precisa
persistir. Visão calculada não se arrasta.

**Automação varrendo tudo, com exclusão por etapa.** Era a forma original do
pedido. Descartada como padrão porque obriga a pessoa a excluir "Em Andamento",
"Concluídas" e "Cancelado" na mão para o produto parar de brigar com ela — o
padrão erra e o usuário conserta. As travas estruturais resolvem os dois últimos;
o opt-out continua existindo para o que sobra, que é escolha de verdade.

**Carimbar a data ao mover.** Descartada pelo motivo do §"tarefa sem data".

## Consequências

- **A favor:** some a faxina diária; a etapa passa a ter significado único e
  verificável; reagendar vira um arrasto; nenhuma infraestrutura nova.
- **Contra:** a etapa deixa de ser um espaço livre — quem usava "Para amanhã"
  como gaveta de qualquer coisa vai ver a madrugada discordar. O opt-out é a
  saída, e ela é por etapa, não por tarefa.
- **Declarado:** tarefa em etapa travada nunca sai sozinha, mesmo que a data
  mude; tarefa sem data fica sem data.
