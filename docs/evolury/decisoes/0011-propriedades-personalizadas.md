# ADR 0011 — Propriedades personalizadas

- **Status:** Aceito (14/08/2026)
- **Contexto:** funcionalidade [propriedade-personalizada](../funcionalidades/propriedade-personalizada/especificacao.md)
- **Relacionado:** [ADR 0004](0004-idioma-unico-pt-br.md) (idioma), [ADR 0005](0005-semana-comeca-no-domingo.md) (semana), [ADR 0006](0006-fusos-do-brasil.md) (fuso), [ADR 0009](0009-botao-concluir-tarefa.md) (conclusão), [ADR 0010](0010-tarefas-recorrentes.md) (recorrência)

## Contexto

O produto precisa guardar, na tarefa, dado que é do cliente e não do Plane: o
valor do contrato, a data do aceite, o canal de origem, a categoria interna.
Hoje isso vira texto na descrição — invisível para filtro, para agrupamento e
para qualquer relatório.

A edição paga do Plane tem algo parecido, atrelado a "tipos de tarefa" e à
hierarquia que vem com eles. O levantamento no código mostrou dois fatos que
moldam a decisão:

1. **Não há nada a reaproveitar.** Existem `IssueType` e `ProjectIssueType`,
   herdados, mas **nenhum** modelo de propriedade nem de valor. Também não há o
   que quebrar.
2. **Toda a superfície que o recurso toca é lista fixa.** Filtro, agrupamento,
   ordenação, exportação, atividade e webhook são, cada um, um mapa com uma
   entrada por campo conhecido. Nenhum deles é extensível hoje, e é isso — não
   o modelo de dados — que define o tamanho do trabalho.

E existe um molde pronto no próprio código: `Estimate` + `EstimatePoint` já é
"configuração por projeto + tabela de opções + valor por tarefa".

## Conferido contra o mercado (14/08/2026)

| Produto     | Tipos                                                     | O que ensina                                                                                               |
| ----------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Asana**   | 7 — texto, número, data, única, múltipla, pessoa, fórmula | Fórmula é read-only e sempre numérica. Teto de 100 por projeto. Converter única→múltipla não existe.       |
| **Jira**    | ilimitado                                                 | O custo não é o campo, é o **contexto**: criação caiu de 12–13 s para ~2 s ao tirar campos não usados.     |
| **ClickUp** | muitos, incl. moeda                                       | Moeda declara `currency_type` **e** `precision`. Fórmula com `TODAY()` não ordena, não filtra, não agrupa. |
| **monday**  | dezenas                                                   | Coluna fórmula não pode ser espelhada; valor espelhado se comporta mal em fórmula e painéis.               |
| **Linear**  | **nenhum**                                                | Deliberado — usa etiquetas. Quem recria a complexidade do Jira vê as pessoas pararem de seguir o processo. |

## Decisão

### A propriedade é do projeto

É a lição mais cara do Jira: o que degrada não é a quantidade de campos, é a
quantidade de campos **no contexto** de cada tarefa. A recomendação deles é um
campo em menos de dez projetos; a nossa resposta é não ter contexto global
nenhum.

Casa com o resto do produto: etapa, etiqueta e estimativa já são do projeto. E
casa com o teto de consultas que a base já cobra — projeto é a fronteira em que
tudo aqui já é carregado em bloco.

**Reuso entre projetos fica de fora**, e com ele a "biblioteca de campos" do
Asana. Sem ela não pagamos o preço do contexto global, e ela pode entrar depois
sem migração destrutiva: uma propriedade compartilhada é uma linha a mais
apontando para a mesma definição.

### Seis tipos, e o que fica de fora

**Texto, número, data, seleção única, seleção múltipla e moeda.**

O corte não é de preguiça, é a leitura do Linear aplicada: o pedido foi um
formato **mais simples** que o da edição paga, e simples aqui significa poucos
tipos que funcionam em todo lugar — filtro, agrupamento, ordenação, exportação
— em vez de muitos tipos que funcionam em alguns.

- **Pessoa** fica fora porque herda inteiro o problema que a [F5 da
  recorrência](0010-tarefas-recorrentes.md) resolveu: remover alguém do projeto
  não desfaz atribuição, e o valor vira um fantasma. Entra quando entrar com
  essa regra junto, não antes.
- **Fórmula e rollup** ficam fora porque são a fonte de defeito dos quatro
  concorrentes ao mesmo tempo — read-only no Asana, sem ordenar/filtrar/agrupar
  no ClickUp, sem espelhar no monday. E o valor deles depende de já existirem
  campos numéricos maduros, que é o que esta versão cria.
- **Checkbox** fica fora porque seleção única com dois valores já é isso, e com
  rótulos que a equipe escolhe ("Sim/Não" mente menos que um quadrado marcado).

### O valor mora em colunas tipadas

A decisão técnica central, e a que é cara de mudar depois. Três caminhos foram
considerados:

| Caminho                     | Por que não                                                                                         |
| --------------------------- | --------------------------------------------------------------------------------------------------- |
| JSON em `issues`            | barato de ler, péssimo de filtrar e ordenar — e `issues` é a maior tabela do banco                  |
| Uma coluna `value` de texto | ordenar número e data vira cast em toda consulta, e dinheiro em texto é defeito esperando acontecer |
| **Colunas tipadas**         | **escolhido**                                                                                       |

Cada tipo guardado no tipo nativo: `value_text`, `value_number` (decimal),
`value_date`, `value_option` (chave estrangeira) e uma relação para a seleção
múltipla. Índice funciona, ordenação é a do banco, e o filtro não precisa
converter nada.

**Dinheiro em `DECIMAL`, nunca em ponto flutuante.** É o defeito mais antigo do
ofício e o mais fácil de evitar no dia da criação da tabela.

### Moeda é declarada na propriedade

Uma propriedade "Valor do contrato" é em reais **ou** em dólares, com um número
fixo de casas — não uma escolha por tarefa. Guardar a moeda no valor abriria a
porta para somar reais com dólares numa coluna só, que é uma conta errada que
ninguém percebe.

É o formato do ClickUp (`currency_type` + `precision`), e é o que permite somar
a coluna com sentido.

### Obrigatória na criação, nunca na conclusão

Propriedade marcada como obrigatória bloqueia **criar** a tarefa sem ela — é
onde a informação está fresca e o custo de pedir é baixo.

**Não bloqueia concluir.** É a mesma regra que o ADR 0010 aplicou à remoção de
membro: o ato nunca é bloqueado, a consequência nunca é silenciosa. Travar a
conclusão por causa de metadado transforma a configuração de um admin numa
parede na frente de quem terminou o trabalho — e a saída mais rápida da parede
é preencher qualquer coisa, que é pior que o campo vazio.

### Configurar é porta de admin

Como recorrência e automações. Criar propriedade cria trabalho para os outros:
todo mundo passa a ver o campo, e o obrigatório passa a barrar criação. Quem
preenche **valor** é qualquer pessoa que pode editar a tarefa.

### Trocar o tipo é proibido, com uma exceção

Depois de criada, a propriedade não muda de tipo. Converter texto em número não
tem resposta certa para o que já foi escrito, e a "resposta certa" que a
interface escolhesse seria perda silenciosa de dado.

A exceção é **seleção única → múltipla**, que não perde nada: cada valor único
vira uma lista de um. O caminho de volta continua proibido, porque ele perde.

É o mesmo lugar onde o Asana parou — a diferença é que lá a conversão que não
perde dado também não existe, e é pedido antigo do fórum.

### Excluir opção em uso avisa, e não bloqueia

Excluir uma opção usada por tarefas **é permitido**, e a confirmação diz
quantas tarefas perdem o valor. Bloquear criaria o incentivo perverso de
sempre: a saída mais rápida do bloqueio seria apagar a propriedade inteira.

Terceira aplicação da mesma regra deste ADR e do 0010: **o ato administrativo
nunca é bloqueado, a consequência dele nunca é silenciosa.**

### Teto de 30 propriedades por projeto

O Asana corta em 100. Somos o formato simples, e o teto é o que protege a
tabela — trinta colunas já é mais do que cabe numa tela — e a leitura em bloco.

## Alternativas consideradas

- **Propriedade do workspace, disponível em todos os projetos**: é o contexto
  global do Jira, com o custo medido por eles. Descartado.
- **Atrelar propriedades a tipos de tarefa** (modelo da edição paga): amarra
  duas decisões independentes. Quem quer "valor do contrato" não quer,
  necessariamente, criar um tipo de tarefa novo. Descartado.
- **Usar etiquetas para tudo** (modelo do Linear): funciona para categoria e
  não funciona para data nem para dinheiro — etiqueta não ordena nem soma.
  Descartado, mas a filosofia foi adotada no corte de tipos.
- **JSON na tarefa**: ver acima.

## Consequências

- **Toda a superfície fixa vira extensível**: filtro, agrupamento, ordenação,
  exportação, atividade e webhook são hoje um mapa por campo conhecido. Este é
  o volume real do trabalho, e não o modelo de dados.
- **Nenhuma leitura pode custar consulta por tarefa.** Os layouts carregam
  centenas de tarefas, e a base já fixa teto de consultas em teste. Os valores
  vêm em bloco, por página de tarefas.
- **A cópia da recorrência leva os valores** — eles descrevem o trabalho, que é
  o critério do ADR 0010. E precisam ir em bloco: a cópia custa 8 consultas por
  nó hoje, e esse número está fixado em teste.
- **Mudança de valor gera atividade.** Valor de propriedade sem histórico é
  buraco no rastro de uma tarefa que passou a carregar dado de negócio.
- **A exclusão lógica precisa de filtro explícito** nas junções de valor: é a
  armadilha que já mordeu esta base duas vezes, e junção não passa pelo manager.
- **Espaço público fica de fora da v1**: o que é interno não vaza por acidente.
- **Data personalizada não entra em calendário e cronograma na v1.** Os dois
  layouts são construídos sobre `start_date` e `target_date`; generalizá-los é
  trabalho próprio, e sem ele a data personalizada ainda filtra, ordena e sai
  na exportação.
