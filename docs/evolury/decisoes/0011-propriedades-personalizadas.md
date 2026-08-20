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

### Filtrar e agrupar: um prefixo só, e duas portas

A chave de uma propriedade é `property_<uuid>` **em todo lugar** — no
`group_by`, na ordenação (`property__<uuid>`, com `__` porque ali é caminho de
ORM), no parâmetro de consulta e na árvore de filtros ricos. O upstream tinha
deixado um prefixo próprio (`customproperty_`) reservado na edição paga; manter
dois prefixos para o mesmo conceito custaria mais do que a linha que ensina o
adaptador a aceitar o nosso.

A API atende por **duas portas**, porque a base tem duas:

1. **Parâmetro de consulta** (`?property_<id>=opção`), que é como os endpoints
   herdados filtram. Cada condição é aplicada em sua própria chamada.
2. **Árvore de filtros ricos**, que é o que a tela usa: ela manda a árvore
   inteira em `filters`, como JSON, e o backend a valida contra o FilterSet
   antes de virar `Q`.

Na segunda porta a condição precisa nascer como **subconsulta**, não como
junção. A árvore inteira vira um `Q` só, aplicado numa chamada de `.filter()`,
e duas junções ali recairiam na mesma linha da tabela de valores — "canal =
indicação E etiqueta = urgente" devolveria vazio justamente para a tarefa que
tem as duas. A subconsulta ainda resolve de graça a armadilha da exclusão
lógica: junção não passa pelo gerente do modelo, subconsulta escrita à mão sim.

### Agrupar virou opt-in por propriedade (19/08/2026)

Toda propriedade de seleção única aparecia automaticamente em "agrupar por".
Passou a depender de uma marca na definição, `show_in_grouping`, irmã de
`show_on_card` — e com o padrão **invertido**: nasce ligada.

A inversão não é inconsistência, é o custo de cada uma. Uma pastilha a mais
disputa a largura do cartão com todas as outras; um agrupamento a mais é uma
linha num menu que só quem abre vê. E nasce ligada também porque **já era assim
antes da marca existir**: a migração liga para todas, e nenhum agrupamento em
uso desaparece de um menu sem ninguém ter pedido.

**A marca é honrada no servidor, e não só no menu.** Ela entrou em
`alias_de_agrupamento`, que é a mesma função que a allowlist do paginador
consulta (ver a seção seguinte): desmarcar deixa de ser sugestão de tela e vira
recusa da consulta, venha o pedido da tela, de uma URL colada ou de um script.
Esconder no menu e aceitar no servidor seria a forma de guarda que este projeto
não escreve.

No mesmo dia, **subagrupar** passou a oferecer as propriedades e **arrastar o
cartão** passou a gravar o valor. Nenhuma das duas exigiu mecanismo novo: o
servidor já tratava `sub_group_by` simetricamente desde o começo, e o arrasto
reusa o endpoint de valor — que é o que faz o histórico e as automações saírem
idênticos ao caminho do painel da tarefa.

O arrasto **não** é silencioso, ao contrário do arrasto entre etapas pessoais de
"Minhas tarefas" ([ADR 0001](0001-minhas-tarefas-overlay-pessoal.md)). A
distinção é a mesma de sempre: etapa pessoal é organização de uma pessoa, valor
de propriedade é dado do projeto.

### O nome do campo não cabe na allowlist — e não precisa caber

Agrupar e filtrar por campo arbitrário é a família do GHSA-wwgj-929g-42cm, e a
defesa da base é uma allowlist de nomes. Um id de propriedade **não pode**
entrar nela: ele só existe em tempo de execução.

A regra que adotamos é que a chave passe pela **mesma prova, por outro
caminho**: ser um UUID bem formado e existir como propriedade, verificado antes
de qualquer coisa tocar o ORM. Nada do texto que veio do pedido vira caminho de
campo. Na árvore de filtros, a validação do upstream continua comparando nomes
— o que ela compara é um campo-sentinela fixo, para o qual a chave só é
traduzida **depois** de provada.

### A união fechada aceitou um padrão

`TIssueGroupByOptions` e `WORK_ITEM_FILTER_PROPERTY_KEYS` são uniões fechadas, e
eu havia registrado que caber ali exigiria alargá-las para `string` —
refatoração atravessando filtro, agrupamento e visões salvas.

Estava errado. Uma união aceita um membro de **padrão** (`` `property_${string}` ``):
continua fechada ao que o compilador reconhece, continua estreitando nos
`switch`, e o custo medido foi de dois erros de compilação no repositório
inteiro. Fica registrado porque a estimativa foi por inferência, e o
compilador teria respondido em minutos.

### Quem integra precisa do campo, e não só do valor

`property_values` devolve `{"<uuid>": "<uuid>"}`. Para o produto isso basta — a
tela já tem as definições. Para quem integra, são dois ids opacos.

A resposta é diferente nos dois lugares, porque a pergunta é diferente:

- **Webhook**: a carga leva a definição dos campos que **aquela tarefa**
  preenche. O receptor de um webhook nem sempre pode chamar de volta — pode não
  ter credencial, pode estar atrás de uma fila —, e uma carga que exige uma
  segunda chamada para ser entendida é uma carga pela metade. Só os campos
  preenchidos: levar as 30 do projeto em toda tarefa seria fazer todo mundo
  pagar pelo caso raro.
- **API pública**: endereço próprio para as definições. Quem lista tarefas já
  faz chamadas; repetir as mesmas 30 definições dentro de cada uma das 100
  tarefas da página seria desperdício. Definição muda pouco, e endereço próprio
  é o que se pode ler uma vez e guardar.

Os dois são **só leitura**. Criar definição é configuração de projeto, com
regras que já vivem no caminho da tela — nome único, tipo que não muda, moeda
obrigatória em campo de moeda. Um segundo caminho de escrita seria um segundo
lugar para essas regras, e o segundo é sempre o que esquece uma.

### A cascata é assíncrona, e a leitura não pode esperar por ela

Excluir uma propriedade apaga os valores dela **em tarefa assíncrona**. Entre o
clique e a tarefa — e para sempre, se ela falhar — o valor continuaria saindo
na API e no webhook com o id de um campo que não existe mais.

Por isso a leitura filtra a exclusão lógica da propriedade explicitamente, e
não confia na cascata. Encontrado no ambiente de desenvolvimento, com um valor
vivo de uma propriedade já excluída: terceira vez que esta armadilha morde a
base, e a segunda dentro desta funcionalidade.

### O ícone é do campo, e a lista é fechada

Todo campo aparecia com o mesmo desenho de etiqueta. Num seletor onde tudo tem
o mesmo ícone, o ícone deixa de informar: quem procura precisa ler cada nome,
que é justamente o trabalho que ele deveria poupar.

Duas decisões, e a segunda é a que importa:

1. **Padrão por tipo.** Vazio no banco quer dizer "o padrão do tipo", e não
   "sem ícone" — assim o que já existe continua funcionando sem nenhuma
   escrita, e mudar o padrão de um tipo alcança todo mundo que nunca escolheu.
2. **A escolha é uma chave de lista fechada**, validada no servidor. O ícone
   chega à tela como chave de um mapa de componentes; texto livre vindo do
   banco virando nome de componente é exatamente a classe de coisa que esta
   base não deixa passar. Guardamos a chave e não o desenho: trocar de
   biblioteca um dia é refazer o mapa da tela, não migrar dado.

A regra do "efetivo" mora num lugar só, e a API pública e o webhook devolvem
já resolvido — quem integra não precisa conhecer a convenção do vazio para
desenhar o mesmo que a tela desenha.

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
