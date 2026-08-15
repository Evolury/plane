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
| API pública e webhook       | os valores, só leitura                       |
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
- **Filtrar** (o ícone de funil) lista as propriedades de **seleção**, única ou
  múltipla, com as cores das opções. O filtro entra como qualquer outro, e
  sobrevive ao recarregar a página e a salvar a visão.

Só seleção aparece nos dois menus. Agrupar por um campo de texto ou de dinheiro
criaria uma coluna por valor distinto, que é ruído, e não organização.

Se você desativar uma propriedade que está sendo usada num filtro salvo, a tela
não quebra: aquela condição simplesmente deixa de filtrar.

## Com tarefas recorrentes

Os valores **são copiados** para cada ocorrência, inclusive nas subtarefas
aninhadas. Editar o valor na tarefa de origem muda as próximas ocorrências, sem
precisar sincronizar nada.

## O que ainda não existe

- **Filtrar por texto, número, dinheiro ou data nos menus da tela.** A API já
  filtra os quatro (faixa e "contém"); o seletor visual ainda só oferece as de
  seleção.
- Tipo pessoa, fórmula e campo calculado.
- Reaproveitar a mesma propriedade em vários projetos.
- Propriedade de data no calendário e no cronograma.
