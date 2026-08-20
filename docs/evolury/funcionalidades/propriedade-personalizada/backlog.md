# Propriedades personalizadas — Backlog de implementação

Decisão: [ADR 0011](../../decisoes/0011-propriedades-personalizadas.md).
Especificação: [especificacao.md](especificacao.md).
Plano aprovado em 14/08/2026, com as cinco recomendações.

O volume do trabalho **não está no modelo de dados** — está na superfície que
hoje é lista fixa. Filtro, agrupamento, ordenação, exportação, atividade e
webhook são, cada um, um mapa com uma entrada por campo conhecido. É isso que
precisa virar extensível, e é por isso que as fases estão cortadas assim.

## P1 — Modelo e configuração (motor inerte)

- [x] P1.1 Modelos `IssueProperty`, `IssuePropertyOption` e `IssuePropertyValue`,
      com colunas tipadas (`value_text`, `value_number` decimal, `value_date`,
      `value_option`) e a relação de seleção múltipla. Espelha a forma de
      `Estimate` + `EstimatePoint`, que já é config-por-projeto + opções
- [x] P1.2 Migração
- [x] P1.3 CRUD da propriedade, porta de admin: criar, renomear, reordenar,
      ativar/desativar, excluir com aviso de quantas tarefas perdem valor
- [x] P1.4 CRUD das opções, com cor e ordem; excluir opção em uso avisa a
      contagem e não bloqueia
- [x] P1.5 Teto de 30 por projeto, com aviso na tela antes do limite
- [x] P1.6 Trava de troca de tipo, com a exceção seleção única → múltipla
- [x] P1.7 Página "Propriedades" em Configurações → **Estrutura de tarefas**,
      ao lado de etapa, etiqueta e estimativa — as quatro descrevem a tarefa
- [x] P1.8 Testes: os seis tipos, o teto, a trava de tipo, a conversão que não
      perde dado, a exclusão de opção em uso e a porta de admin

Até aqui o recurso é **inerte**: existe configuração e nenhuma tarefa a usa. É
de propósito — dá para revisar o modelo antes de existir dado dependendo dele.

## P2 — Valor na tarefa

- [x] P2.1 Leitura e escrita do valor no painel e no peek, um editor por tipo
- [x] P2.2 Modal de criação, com a obrigatoriedade barrando **só a criação**
- [x] P2.3 Obrigatoriedade não alcança tarefa que já existia
- [x] P2.4 Atividade de mudança de valor, com o rótulo da propriedade
- [x] P2.5 Webhook e API pública carregam os valores — só leitura; escrever
      tem endpoint próprio, com a validação por tipo que a serialização daria a
      volta. A API pública aceita a leitura em bloco pelo contexto
- [x] P2.6 Testes: cada tipo, obrigatório na criação e não na conclusão,
      retroatividade, e o filtro explícito de `deleted_at` nas junções

## P3 — Leitura em bloco e saída do dado

- [x] P3.1 Carga dos valores **em bloco por página de tarefas**, com teto de
      consultas fixado em teste — os layouts carregam centenas de tarefas
- [x] P3.2 Coluna no layout de tabela, uma por propriedade ativa — acoplada
      pela ponta, com provedor de contexto para a carga da página
- [x] P3.3 Chip no cartão de lista e quadro, só nas marcadas para isso
- [x] P3.4 Exportação CSV e XLSX, estendendo `IssueExportSerializer` de
      `utils/porters` — que é o exportador VIVO; o `utils/exporters`, com
      esquema declarativo, não é o que o job usa
- [x] P3.5 Testes: leitura em bloco de 40 tarefas em uma consulta, página de
      30 pelo endpoint, recorte do `card_only`, e a exportação com uma
      consulta de valores para 20 tarefas

## P4 — Filtro, agrupamento e ordenação

- [x] P4.1 Filtro por propriedade — devolve um `Q` por propriedade, aplicado
      em chamada própria de `.filter()`. Duas num `.filter()` só colidiriam
      no mesmo join, e a tarefa que tem as duas coisas sumiria
- [x] P4.2 Agrupar por seleção única — **no backend**. Um alias anotado
      (`property_<uuid>`) resolve `F()`, `values()` e a partição de janela do
      paginador, sem reescrever nada. As colunas seguem a ordem das opções, com
      `"None"` no fim para a tarefa sem valor ter onde caber
- [x] P4.2b Agrupar pela INTERFACE — a propriedade aparece no menu "Agrupar
      por" e o quadro desenha uma coluna por opção. A união fechada não foi
      alargada para `string`: ganhou um membro de PADRÃO (`property_${string}`),
      que continua fechado ao que o compilador reconhece
- [x] P4.3 Ordenar por número, data, moeda, texto e seleção — prefixo
      `property__<uuid>` resolvido ANTES da allowlist, com o id validado como
      UUID e a propriedade conferida no banco antes de tocar no ORM. Ordena
      pela coluna tipada, e seleção ordena pela ordem das opções
- [x] P4.4 Filtros ricos no front — a propriedade de seleção aparece no
      seletor de filtro, com as opções e as cores dela, e a condição sobrevive
      ao recarregamento da página. Mesmo membro de padrão do P4.2b
- [x] P4.4b Filtro pela ÁRVORE de filtros ricos — a tela manda a árvore
      inteira em `filters`, como JSON, e não um parâmetro por filtro. A
      condição de propriedade nasce como SUBCONSULTA para compor sob
      `and`/`or`/`not` sem colidir consigo mesma no join
- [x] P4.5 Testes: cada operador de cada tipo, duas propriedades ao mesmo
      tempo, e filtro forjado que nunca vira consulta — pelos DOIS caminhos
      (parâmetro de consulta e árvore de filtros ricos)

## P5 — Integração com a recorrência

- [x] P5.1 A cópia da ocorrência leva os valores (ADR 0010: o que descreve o
      trabalho copia)
- [x] P5.2 Em bloco, sem estourar o custo por nó fixado em teste (8 consultas)
- [x] P5.3 Testes: valores na ocorrência, na subtarefa aninhada, e o custo

## P7 — Os campos para quem integra

- [x] P7.1 Webhook leva a DEFINIÇÃO dos campos que a tarefa preenche — nome,
      tipo, rótulo e cor das opções. O receptor não tem como chamar de volta
- [x] P7.2 Recorte: só as propriedades preenchidas, e uma consulta de valores
      por tarefa (não duas, depois de dois métodos passarem a lê-los)
- [x] P7.3 API pública: endereço próprio para as definições, só leitura, na
      ordem da tela
- [x] P7.4 Valor de propriedade excluída para de sair — a cascata é assíncrona
      e a leitura não pode esperar por ela
- [x] P7.5 Testes: carga que se explica, recorte, lote com cache por tarefa,
      teto de consultas, 405 na escrita, e projeto alheio

## P8 — O ícone do campo

- [x] P8.1 Padrão por TIPO, para dois campos nunca nascerem com o mesmo desenho
- [x] P8.2 Escolha explícita, guardada como chave de uma lista fechada — texto
      livre viraria nome de componente vindo do banco
- [x] P8.3 O ícone aparece na configuração, no painel, no cabeçalho da tabela e
      no seletor de filtro (onde era etiqueta para todas)
- [x] P8.4 A API pública e o webhook devolvem o ícone EFETIVO — quem integra não
      precisa conhecer a regra do padrão
- [x] P8.5 Testes: um padrão por tipo sem repetição, escolha vencendo o padrão,
      chave forjada recusada, e o padrão sempre dentro da lista permitida

## P6 — Matriz de compatibilidade

- [x] P6.1 Executar a matriz contra os recursos existentes, com evidência,
      como na F6 da recorrência
- [x] P6.2 Manual do usuário

## Fora de escopo

Tipo pessoa, fórmula, rollup, checkbox, reuso entre projetos, propriedade por
tipo de tarefa, espaço público, e data personalizada em calendário e cronograma
([ADR 0011](../../decisoes/0011-propriedades-personalizadas.md)).

## Lacunas fechadas — e a estimativa que estava errada

As duas lacunas declaradas acima (P4.2b e P4.4) foram fechadas. Vale registrar
por quê, porque a estimativa anterior errou por muito.

Eu havia escrito que `TIssueGroupByOptions` e `WORK_ITEM_FILTER_PROPERTY_KEYS`
são uniões fechadas e que caber ali exigiria alargá-las para `string` — uma
refatoração atravessando toda a filtragem, o agrupamento e as visões salvas.

**Não exigiu.** Uma união aceita um membro de tipo literal de PADRÃO:

```ts
| "team_project"
| `property_${string}`   // continua fechado: é um padrão, não `string`
```

O compilador continua recusando `"qualquer_coisa"` e continua estreitando nos
`switch`. O custo medido foi de **dois** erros de compilação no repositório
inteiro, não a refatoração que eu previa. A lição não é sobre tipos: é que eu
declarei um bloqueio por inferência em vez de medir com o compilador — que
levaria minutos.

## P9 — Os outros tipos no seletor de filtro

- [x] P9.1 **Data** no seletor, com "é" e "entre" — reaproveita o construtor do
      produto, e o backend passou a aceitar `__exact` e `__range` (a faixa vira
      o mesmo par `gte`/`lte` do caminho por parâmetro)
- [x] P9.2 **Texto, número e moeda** — o pacote de filtros ricos ganhou o
      formato que faltava: campo de DIGITAR. Texto filtra por trecho, número e
      moeda por igualdade e faixa, e a moeda mostra o símbolo no campo

## A barreira que eu declarei e que não existia

Vale registrar, porque o erro foi de método.

Ao tentar a primeira vez, alarguei as uniões de configuração por operador e o
TypeScript passou a quebrar arquivos do próprio upstream. Concluí que mexer ali
era inviável e documentei isso como bloqueio.

**Era um genérico meu com o padrão errado.** O núcleo declara as uniões com
`<TFilterValue>` explícito; eu usei o padrão do meu tipo, que era `<string>`.
Como `createFilterFieldConfig` devolve a união INTEIRA de formatos, um membro
com genérico incompatível derruba a restrição em todos os pontos de uso — daí
os erros aparecerem em arquivos que eu não tinha tocado.

Corrigido o genérico, a extensão coube nos pontos que o upstream deixou vazios,
sem nenhuma mudança no núcleo. O que eu chamei de "trabalho nos genéricos do
pacote compartilhado, com regressão em quem já os usa" era uma linha.

A lição: quando o compilador acusa erro em arquivo alheio depois de uma
extensão minha, a primeira hipótese é que a extensão está mal declarada — não
que o alheio é frágil.

## Achado colateral, já corrigido

O seletor de filtros não abria no servidor de desenvolvimento: o
`WorkItemFiltersHOC` criava a instância num `useMemo` e a apagava no `cleanup`
do efeito, e o `StrictMode` — que monta, desmonta e remonta o mesmo fiber —
deixava uma referência órfã.

Corrigido em 15/08/2026: o efeito passou a recriar ao montar, e a renderização
lê a instância viva do store. `useMemo` não é dono de ciclo de vida.

## P10 — A propriedade como eixo do quadro — 19/08/2026

O pedido: usar propriedade personalizada como **etapa de fluxo**, com um projeto
só em vez de um projeto por fluxo. A medição feita antes de planejar mostrou que
faltava menos do que parecia — agrupar já funcionava, e o servidor já tratava
`sub_group_by` simetricamente desde o P4.2.

- [x] P10.1 **Subagrupar por propriedade** — só faltava o menu.
      `sub-group-by.tsx` montava a lista direto de `ISSUE_GROUP_BY_OPTIONS`;
      passou a usar o mesmo `useGroupByOptions` do "Agrupar por". Um arquivo, e
      as raias já sabiam se desenhar. De quebra, "Nenhum" voltou a ser a última
      linha: entrando depois dela, as propriedades empurravam a opção de
      desligar para o meio do menu
- [x] P10.2 **Escolher, na definição, se a propriedade agrupa** —
      `show_in_grouping`, irmã de `show_on_card`, com o padrão **invertido**:
      nasce ligada, e a migração liga para as que já existiam. Honrada em
      `alias_de_agrupamento`, que é a mesma função que a allowlist do paginador
      consulta — desmarcar vira 400, não só um item a menos no menu
- [x] P10.3 **Arrastar o cartão muda o valor** — quadro e lista. Três pontos:
      `DRAG_ALLOWED_GROUPS` virou função (`podeArrastarNoAgrupamento`), porque
      lista fixa não comporta id de tempo de execução; `campoDoAgrupamento`
      resolve a chave para o próprio nome do campo anotado pelo servidor, e é o
      que faz `updateIssueList` reagrupar o cartão sozinho; e a escrita saiu do
      PATCH em `updateIssueOnDrop`, onde ciclo e módulo já saíam pelo mesmo
      motivo — não são campo da tarefa. Soltar em "Nenhum" apaga
- [x] P10.4 Testes de contrato (recusa do servidor, ida e volta do campo pela
      API, padrão ligado) e de unidade no front (chave, arrasto liberado, campo
      do agrupamento, filtro do menu). Cada guarda provada por injeção de
      defeito, **uma de cada vez**
- [x] P10.5 Verificação na tela, contra o `planedev`: menu, raias, arrasto de
      um e de dois eixos, "Nenhum" apagando, a marca escondendo dos dois menus,
      a URL recusada com 400 — e o caso que motivou tudo, um **módulo** com o
      quadro agrupado por "Canal"

**O que ficou de fora:** seleção múltipla continua sem agrupar. Ela duplicaria o
cartão entre colunas, como etiqueta, e aí arrastar não teria resposta certa —
acrescenta ou substitui? Sem resposta boa, não entra.

**Lacuna registrada:** cartão movido em outra aba não troca de coluna sozinho.
Está no [backlog técnico](../../backlog-tecnico.md), com o motivo e o caminho.

## P11 — O histórico que era gravado e nunca aparecia — 20/08/2026

Relatado como "arrastar entre etapas não registra nada nas atividades". A
medição mostrou outra coisa: **a linha sempre foi gravada** — desde a v1.13.0, e
igual pelos três caminhos de escrita (painel, automação e agora o arrasto). Quem
não a mostrava era a tela.

As três telas de atividade despacham por **campo conhecido** e devolvem nada
para o resto (`default: return null`). O campo aqui é o NOME de uma propriedade
do cliente, que nenhuma lista pode conter — então toda mudança de propriedade
era escrita e engolida, em toda parte.

- [x] P11.1 **Verbo próprio** (`property_updated`) em
      `registrar_atividade_de_propriedade`, mais o id da propriedade em
      `new_identifier`. Um fallback genérico foi descartado com medição: quem
      cai no `default` inclui `field="issue"` (exclusão de tarefa) e qualquer
      campo que o upstream venha a rastrear
- [x] P11.2 **A linha desenhada** nas duas telas — histórico da tarefa e
      "Minhas atividades" —, em três frases conforme o caso: "definiu Canal
      como X", "alterou Canal de X para Y", "limpou Canal". Frase única com
      pedaços vazios produzia "alterou Canal de para Anúncio"
- [x] P11.3 **Migração 0149** para o histórico já gravado: casa por
      **(projeto, nome)** e só toca `verb="updated"` sem `new_identifier`.
      Propriedade renomeada não é alcançada, e é aceito — a linha antiga guarda
      o nome de quando a mudança aconteceu, e inventar vínculo por semelhança
      seria adivinhar
- [x] P11.4 Testes de contrato, com a regra da migração extraída para
      `marcar_atividades_de_propriedade` — o `pytest.ini` roda com
      `--nomigrations`, então regra escrita dentro da migração não é executada
      por teste nenhum (a lição da 0147)

**O deploy revelou um efeito não planejado, e ele é o desejado.** Em produção a
migração marcou também o histórico de **propriedades apagadas** — "Botão",
"Dinhe" e "Loca". O motivo é que `apps.get_model` devolve o modelo histórico
sem o gerente de exclusão lógica, então `.all()` enxerga as apagadas.

Fica como está: história de propriedade apagada continua sendo história, e
escondê-la seria apagar o que de fato aconteceu. A imprecisão teórica é um nome
repetido entre uma propriedade viva e uma apagada no mesmo projeto — a restrição
de unicidade só vale para as vivas, então o par é possível, e o índice ficaria
com uma das duas. O rótulo exibido seria idêntico nos dois casos, e nada
dereferencia o `new_identifier` hoje. **Medido na produção: 0 ocorrências.**

**Uma injeção passou, e o teste foi refeito.** Remover a guarda do
`new_identifier` não derrubou nada: o que protegia a atividade de etiqueta era o
casamento por nome, não a guarda. O teste passou a criar uma propriedade
chamada `labels` — a colisão em que a guarda é o que de fato protege — e aí a
injeção falhou como devia.
