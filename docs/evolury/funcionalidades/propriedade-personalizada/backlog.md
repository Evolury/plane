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
- [ ] P4.2 Agrupar por seleção única — **não entrou**. Atravessa o `grouper`,
      o paginador (que usa o nome do campo em `F()`, `values()` e na partição
      de janela) e o menu do front. É tratável com um alias anotado, mas é
      mudança no caminho quente e paginado, e pede validação própria
- [x] P4.3 Ordenar por número, data, moeda, texto e seleção — prefixo
      `property__<uuid>` resolvido ANTES da allowlist, com o id validado como
      UUID e a propriedade conferida no banco antes de tocar no ORM. Ordena
      pela coluna tipada, e seleção ordena pela ordem das opções
- [ ] P4.4 Filtros ricos no front — **não entrou**. O filtro existe e está
      testado na API; falta o seletor visual, que depende do sistema de
      filtros ricos e de um editor por tipo
- [x] P4.5 Testes: cada operador de cada tipo, duas propriedades ao mesmo
      tempo, e filtro forjado que nunca vira consulta

## P5 — Integração com a recorrência

- [x] P5.1 A cópia da ocorrência leva os valores (ADR 0010: o que descreve o
      trabalho copia)
- [x] P5.2 Em bloco, sem estourar o custo por nó fixado em teste (8 consultas)
- [x] P5.3 Testes: valores na ocorrência, na subtarefa aninhada, e o custo

## P6 — Matriz de compatibilidade

- [x] P6.1 Executar a matriz contra os recursos existentes, com evidência,
      como na F6 da recorrência
- [x] P6.2 Manual do usuário

## Fora de escopo

Tipo pessoa, fórmula, rollup, checkbox, reuso entre projetos, propriedade por
tipo de tarefa, espaço público, e data personalizada em calendário e cronograma
([ADR 0011](../../decisoes/0011-propriedades-personalizadas.md)).

## Lacunas conhecidas

Duas, ambas declaradas e nenhuma bloqueando o uso do que foi entregue:
**agrupar por propriedade** (P4.2) e **filtrar pela interface** (P4.4). O
raciocínio de cada uma está na linha correspondente e na
[matriz de compatibilidade](compatibilidade.md).
