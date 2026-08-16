# Automações personalizadas — manual

O comportamento observável, em linguagem de quem usa. Decisão:
[ADR 0012](../../decisoes/0012-automacoes-personalizadas.md).

## O que é

Regras que o seu time escreve, no formato **quando / se / então**:

> **Quando** a prioridade mudar para Urgente, **se** a tarefa for do setor
> Comercial, **então** mover para Em andamento e atribuir a quem mudou.

Diferente das duas automações fixas que já existiam (arquivar e fechar tarefas
paradas), aqui quem decide o que acontece é você.

## Onde se configura

**Configurações do projeto → Execução → Automações**, abaixo das duas fixas.

Criar, editar, ligar e desligar é **só para admin do projeto** — uma regra
descreve o processo do time e às vezes carrega decisão de gestão.

## Quando (o gatilho)

| Gatilho                   | Dispara quando                                                     |
| ------------------------- | ------------------------------------------------------------------ |
| **Uma tarefa for criada** | qualquer tarefa nova no projeto. Rascunho **não** dispara.         |
| **Um campo for alterado** | você escolhe o campo, e opcionalmente só quando ele virar um valor |
| **Alguém comentar**       | um comentário novo na tarefa                                       |
| **Em um horário**         | todo dia, ou em dias escolhidos da semana, numa hora               |

Tarefa nascida de uma **recorrência** não dispara a regra de "tarefa criada",
porque a origem daquela série já é um molde preenchido. Se você quiser o
contrário, marque "valer também para tarefas de recorrência" na própria regra.

O horário do gatilho agendado é o do **fuso do projeto**: "toda manhã às 8h" é
8h de quem lê o quadro. A varredura roda de quinze em quinze minutos, então a
regra dispara na primeira passagem depois da hora marcada. Se o servidor ficar
fora do ar, a rodada seguinte roda **uma vez** — atraso não acumula.

O campo pode ser estado, prioridade, responsáveis, etiquetas, data de início,
vencimento, ciclo, módulo — **ou qualquer propriedade personalizada do
projeto**. Renomear a propriedade ou o estado não quebra a regra.

Deixar "só quando mudar para" vazio significa "qualquer mudança neste campo".

## Se (a condição)

É a **mesma linha de filtros do quadro**. Tudo que você filtra na tela, filtra
aqui: estado, prioridade, responsável, etiqueta, ciclo, módulo, datas e as
propriedades personalizadas.

Sem condição, a regra vale para toda tarefa que disparar o gatilho.

O botão **Simular** responde "quantas tarefas se encaixam agora", sem escrever
nada — é a forma de descobrir o alcance da condição antes de ligar a regra.

## Então (as ações)

Mudar o estado · mudar a prioridade · mudar responsáveis · mudar etiquetas ·
definir data (fixa ou "daqui a N dias") · preencher propriedade personalizada ·
**comentar** · **notificar** · **arquivar** · **incluir no ciclo ativo**.

No texto de comentário e de notificação você pode usar cinco variáveis:
`{{tarefa}}`, `{{responsável}}`, `{{quem_disparou}}`, `{{estado}}` e
`{{vencimento}}`. O que não estiver nessa lista fica escrito como está — não
existe linguagem de fórmula aqui, de propósito.

**Notificar** avisa quem a regra escolheu (pessoas, os responsáveis, quem criou,
quem disparou), no sino e por e-mail. É diferente do aviso automático que
qualquer mudança já gera: aquele vai para quem _acompanha_ a tarefa.

**Criar tarefa** e **criar subtarefas** existem só em regra de **evento** — a
criação por horário é o que as Tarefas recorrentes fazem, com calendário e
controle de ocorrência aberta, e a combinação nem aparece no menu.

Uma regra cria o conjunto **uma vez por tarefa**: mover para Homologação, voltar
e mover de novo não recria o checklist. Acrescentar um item à regra e disparar de
novo cria só o item novo. A tarefa criada nasce na etapa padrão do projeto, pode
herdar os responsáveis do pai e pode vencer em N dias contados da criação — e
**nunca** vira uma tarefa recorrente.

Subtarefa não é criada na tarefa que é **origem de uma recorrência ativa**: ali,
uma subtarefa nova mudaria todas as ocorrências futuras. O registro diz isso.

**Arquivar** só age em tarefa concluída ou cancelada. **Incluir no ciclo** usa o
ciclo ativo no momento da execução — nunca um ciclo escolhido de véspera, que
envelheceria na virada. **Incluir no módulo**, ao contrário, usa o módulo que
você escolhe na regra: módulo é contêiner durável, e o que você escolhe hoje
continua certo daqui a seis meses.

## Não sabe por onde começar

A tela vazia mostra seis **receitas prontas**. Um clique abre o editor já
preenchido, com o que depende do seu projeto — qual estado, qual etiqueta —
deixado para você escolher.

As ações rodam **na ordem em que aparecem**, e cada uma enxerga o que a anterior
fez.

Em responsáveis, além de escolher pessoas você pode escolher dois **papéis**,
resolvidos na hora: _quem criou a tarefa_ e _quem disparou a regra_. Isso
continua certo mesmo quando as pessoas do time mudam.

## O que aparece no histórico da tarefa

A mudança feita por uma regra é creditada a **Automação**, e não a você nem a
quem criou o projeto. Assim dá para separar, na linha do tempo, o que uma pessoa
fez do que uma regra fez.

## "Por que a minha regra não rodou?"

Abra a regra e vá em **Execuções**. Cada linha diz o que aconteceu:

- **Executada** — a regra rodou. Abaixo, o que cada ação fez.
- **Condição não casou** — o gatilho disparou, mas a tarefa não se encaixava.
  É o caminho normal, não é erro.
- **Falhou** — algo deu errado; a mensagem explica o quê.

Dentro de "Executada", uma ação pode aparecer como **"já estava assim"**: a
regra rodou e não mudou nada porque o valor já era o esperado. É o que explica
uma regra que roda todo dia sem mexer em nada.

## Por quanto tempo o registro fica

Execução que **fez algo** (ou tentou e falhou): 30 dias. Execução que **parou na
condição**: 7 dias — ela responde "por que não rodou?", pergunta que se faz
enquanto se escreve a regra, e é a que enche a lista.

O que a regra mudou na tarefa continua no **histórico da tarefa**, para sempre;
o registro de execuções é a visão pela regra, não pela tarefa.

## Travas que existem para o seu bem

- Uma regra **não responde ao que ela mesma fez**.
- Encadeamento entre regras tem **fundo**: até três voltas.
- Se uma regra passar de **200 execuções em uma hora**, ela se **desliga
  sozinha** e o motivo aparece na lista. Isso protege contra uma edição em massa
  virar uma tempestade.

## Limites conhecidos

- Não existe "se/senão" dentro de uma regra. Use duas regras.
- Não existe espera ("faça isto daqui a 3 dias"). O gatilho agendado resolve
  esse caso e chega na próxima entrega.
- Não existe linguagem de fórmula. As ações são seletores.
