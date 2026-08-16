# Propriedades personalizadas — manual

O comportamento observável, em linguagem de quem usa. Decisão:
[ADR 0011](../../decisoes/0011-propriedades-personalizadas.md).

## O que é

Campos seus, guardados na tarefa: valor do contrato, data do aceite, canal de
origem, categoria interna. Diferente de escrever na descrição, eles **filtram,
ordenam, aparecem na tabela e saem na exportação**.

## Onde se configura

**Configurações do projeto → Estrutura de tarefas → Propriedades**, ao lado de
Estados, Etiquetas e Estimativas — as quatro descrevem a tarefa.

Criar, editar e excluir é **só para admin do projeto**. Preencher o valor é de
quem pode editar a tarefa.

Limite de **30 propriedades por projeto**.

## Os seis tipos

| Tipo                 | Serve para                      | Filtra         | Ordena                |
| -------------------- | ------------------------------- | -------------- | --------------------- |
| **Texto**            | observação curta, código        | contém         | A→Z                   |
| **Número**           | quantidade, peso, prazo em dias | faixa          | sim                   |
| **Data**             | aceite, entrega, vencimento     | faixa          | sim                   |
| **Seleção única**    | canal, categoria, origem        | é uma destas   | pela ordem das opções |
| **Seleção múltipla** | marcadores, áreas envolvidas    | tem uma destas | não                   |
| **Moeda**            | valor de contrato, custo        | faixa          | sim                   |

**Seleção única e múltipla têm opções com cor**, e a cor é o que faz o quadro
ser lido de relance.

**Moeda escolhe a moeda e as casas decimais na configuração**, não na tarefa.
Assim a coluna soma com sentido — misturar reais e dólares no mesmo campo daria
um total que ninguém percebe estar errado.

Se você digitar mais casas do que o campo aceita, ele **avisa, não salva e
devolve o valor que estava lá** — em vez de arredondar por conta própria ou
deixar o campo vazio.

O campo também **mostra o número com as casas configuradas**: um campo de duas
casas exibe `100.00`, não `100,000000`.

Campos de digitar (texto, número, data, moeda) **salvam quando você sai do
campo**, ou ao apertar Enter. Escape desfaz o que estava digitando.

**Ordenar por seleção usa a ordem das opções**, e não o alfabeto: se você
arrastou "Urgente" para o topo da lista, a ordenação respeita isso. Tarefas sem
valor vão sempre para o fim, subindo ou descendo.

## O ícone do campo

Cada propriedade tem um ícone, e ele aparece na configuração, no painel da
tarefa, no cabeçalho da coluna da tabela e no seletor de filtro.

**Sem escolher nada, o ícone vem do tipo**: texto é a letra, número é o
cerquilha, data é o calendário, seleção única é a lista, múltipla são as
camadas, moeda é o cifrão. Assim dois campos diferentes nunca nascem com o
mesmo desenho — o que obrigaria a ler o nome de cada um.

Para escolher outro, abra a propriedade e clique em um dos ícones da grade.
São 30, e a lista é fechada de propósito: ícone é configuração, não catálogo.
Um link abaixo da grade devolve o campo ao padrão do tipo.

## Obrigatória

Marcar como obrigatória **impede criar a tarefa** sem preencher.

Ela **não impede concluir**, e **não alcança tarefas que já existiam**. É
deliberado: pôr uma parede na frente de quem terminou o trabalho só ensina a
preencher qualquer coisa, e exigir o campo do passado transformaria uma decisão
de hoje em dívida do projeto inteiro.

Propriedade **desativada** não exige nada — ela sumiu da tela, então não teria
como ser preenchida.

## Onde os valores aparecem

| Lugar                       | O que mostra                                 |
| --------------------------- | -------------------------------------------- |
| Painel e peek da tarefa     | todos os campos ativos, para ler e editar    |
| Modal de criação            | todos os campos ativos                       |
| Cartão da lista e do quadro | **só** as marcadas com "mostrar no cartão"   |
| Layout de tabela            | uma coluna por propriedade ativa             |
| Exportação CSV e XLSX       | uma coluna por propriedade, em texto legível |
| API pública e webhook       | os valores **e a definição dos campos**      |
| Histórico da tarefa         | cada mudança, com o nome do campo            |

**No cartão só aparecem as marcadas** porque trinta campos ali fariam do quadro
uma planilha ruim. Quem quer todos tem o layout de tabela, que é onde a largura
existe.

## Editar a configuração depois

| Mudança                     | Pode?                                         |
| --------------------------- | --------------------------------------------- |
| Renomear, reordenar         | sim                                           |
| Desativar                   | sim — **os valores continuam guardados**      |
| Adicionar ou renomear opção | sim, e vale para as tarefas que já a usam     |
| Excluir opção em uso        | sim, e o aviso diz **quantas tarefas** perdem |
| Excluir a propriedade       | sim, e o aviso diz quantas tarefas perdem     |
| **Trocar o tipo**           | **não** — exceto seleção única → múltipla     |

**Desativar é o meio-termo**: o campo some dos formulários e da tabela, e nada
se perde. É o que fazer quando um campo sai de uso e o histórico importa.

**Trocar o tipo não existe** porque não há resposta certa para o que já foi
escrito — converter texto em número teria de decidir sozinho o que fazer com
"cerca de 30". A única conversão permitida é seleção única → múltipla, porque
ela não perde nada: cada valor vira uma lista de um.

## Agrupar e filtrar por uma propriedade

Na tela de tarefas do projeto:

- **Agrupar por** (menu "Exibir") lista as propriedades de **seleção única**
  junto com estado, prioridade e as demais. O quadro passa a ter uma coluna por
  opção, na ordem em que você as configurou, e uma coluna "Nenhum" no fim para
  as tarefas sem valor.
- **Filtrar** (o ícone de funil) lista as propriedades de **seleção** — única ou
  múltipla, com as cores das opções — e as de **data**, com "é" e "entre". O
  filtro entra como qualquer outro, e sobrevive ao recarregar a página e a
  salvar a visão.

**Agrupar** aceita só seleção única: agrupar por texto, data ou dinheiro criaria
uma coluna por valor distinto, que é ruído, e não organização.

Se você desativar uma propriedade que está sendo usada num filtro salvo, a tela
não quebra: aquela condição simplesmente deixa de filtrar.

## Para quem integra: os campos, e não só os valores

A tarefa sai com os valores em `property_values`, e ali um campo é um id:

```json
"property_values": { "e418d9f0-…": "88590486-…" }
```

Sozinho isso não diz nada. Por isso:

- **No webhook**, a carga leva junto a **definição** dos campos que aquela
  tarefa preenche — nome, tipo e, nas de seleção, o rótulo e a cor de cada
  opção. Quem recebe entende "Canal = Indicação" sem precisar chamar de volta,
  que é o que um webhook nem sempre pode fazer.
- **Na API pública**, as definições do projeto têm endereço próprio:

  ```http
  GET /api/v1/workspaces/<slug>/projects/<id>/issue-properties/
  ```

  Vem na mesma ordem da tela. É o que resolve os ids de `property_values` — e
  como muda pouco, pode ser lido uma vez e guardado.

Os dois são **só leitura**. Criar ou alterar um campo é configuração do
projeto, e tem um caminho só: a tela.

## Com tarefas recorrentes

Os valores **são copiados** para cada ocorrência, inclusive nas subtarefas
aninhadas. Editar o valor na tarefa de origem muda as próximas ocorrências, sem
precisar sincronizar nada.

## O que ainda não existe

- **Filtrar por texto, número ou dinheiro nos menus da tela.** A API já filtra
  os três (faixa e "contém"); o seletor visual oferece seleção e **data**.
- Tipo pessoa, fórmula e campo calculado.
- Reaproveitar a mesma propriedade em vários projetos.
- Propriedade de data no calendário e no cronograma.
