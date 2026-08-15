# Propriedades personalizadas — especificação

Decisão: [ADR 0011](../../decisoes/0011-propriedades-personalizadas.md).

Guardar na tarefa o dado que é do cliente e não do Plane: o valor do contrato,
a data do aceite, o canal de origem, a categoria interna. Hoje isso vira texto
na descrição — invisível para filtro, agrupamento e relatório.

## Onde a propriedade mora

**No projeto**, em Configurações → Execução, ao lado das automações e das
tarefas recorrentes. **Criar, editar e excluir é porta de admin**; preencher
valor é de quem pode editar a tarefa.

Teto de **30 propriedades por projeto**.

## Os seis tipos

| Tipo                 | O que aceita                                    | Filtra        | Agrupa  | Ordena                |
| -------------------- | ----------------------------------------------- | ------------- | ------- | --------------------- |
| **Texto**            | linha única                                     | contém        | não     | A→Z                   |
| **Número**           | inteiro ou decimal                              | faixa         | não     | sim                   |
| **Data**             | uma data, no fuso do projeto                    | faixa         | não     | sim                   |
| **Seleção única**    | uma opção da lista, com cor                     | é / não é     | **sim** | pela ordem das opções |
| **Seleção múltipla** | várias opções da lista                          | tem / não tem | não     | não                   |
| **Moeda**            | decimal, com moeda e casas fixas na propriedade | faixa         | não     | sim                   |

**Agrupar só por seleção única** é decisão: é o único tipo com um conjunto
fechado e pequeno de valores. Agrupar por texto ou por moeda produziria uma
coluna por valor distinto, que é ruído, não organização.

### O que cada propriedade configura

Nome, tipo, obrigatoriedade, ordem de exibição e se aparece no cartão dos
layouts. As de seleção configuram também as **opções**, cada uma com rótulo,
cor e ordem. As de moeda configuram **moeda** (BRL, USD, EUR) e **casas
decimais**.

A moeda é da propriedade, não do valor: "Valor do contrato" é em reais **ou**
em dólares. Guardar moeda por tarefa abriria a porta para somar reais com
dólares numa coluna só — uma conta errada que ninguém percebe.

## Obrigatória: na criação, nunca na conclusão

Propriedade obrigatória **impede criar** a tarefa sem ela. É onde a informação
está fresca e o custo de pedir é baixo.

**Não impede concluir.** Travar a conclusão por causa de metadado põe uma
parede na frente de quem terminou o trabalho, e a saída mais rápida da parede é
preencher qualquer coisa — pior que o campo vazio. Vale a mesma regra do
[ADR 0010](../../decisoes/0010-tarefas-recorrentes.md): o ato nunca é
bloqueado, a consequência nunca é silenciosa.

Tarefa que já existia quando a propriedade obrigatória foi criada **continua
válida**. Obrigatoriedade vale para o que nasce depois; aplicá-la ao passado
transformaria uma configuração de hoje em dívida retroativa do projeto inteiro.

## Depois de criada

| Mudança                               | Permitido                                        |
| ------------------------------------- | ------------------------------------------------ |
| Renomear, reordenar, ativar/desativar | sim                                              |
| Trocar o tipo                         | **não** — exceto seleção única → múltipla        |
| Adicionar opção                       | sim                                              |
| Renomear opção                        | sim, e vale para as tarefas que já a usam        |
| Excluir opção em uso                  | sim, avisando **quantas tarefas** perdem o valor |
| Excluir a propriedade                 | sim, avisando; os valores vão junto              |

**Seleção única → múltipla** é a única conversão porque é a única que não perde
nada: cada valor vira uma lista de um. O caminho de volta perde, e por isso não
existe.

**Desativar** é o meio-termo que preserva: a propriedade some dos formulários e
dos filtros, e os valores continuam gravados. É o que fazer quando um campo sai
de uso sem que ninguém queira apagar o histórico.

## Onde a propriedade aparece

| Lugar                                          | v1                             |
| ---------------------------------------------- | ------------------------------ |
| Painel e peek da tarefa                        | sim                            |
| Modal de criação                               | sim                            |
| Coluna no layout de tabela                     | sim                            |
| Chip no cartão (lista e quadro)                | sim, só nas marcadas para isso |
| Filtro                                         | sim                            |
| Agrupar (seleção única)                        | sim                            |
| Ordenar (número, data, moeda, texto)           | sim                            |
| Exportação CSV e XLSX                          | sim                            |
| API pública e webhook                          | sim                            |
| Histórico de atividade                         | sim                            |
| Espaço público                                 | não                            |
| Calendário e cronograma por data personalizada | não                            |

**A exportação entra na v1 por princípio**: dado que só existe dentro da tela é
dado preso. **A atividade também**: a tarefa passa a carregar informação de
negócio, e mudança sem histórico é buraco no rastro.

**Espaço público fica fora** para que o que é interno não vaze por acidente.
**Calendário e cronograma** são construídos sobre `start_date` e `target_date`;
generalizá-los é trabalho próprio, e sem ele a data personalizada ainda filtra,
ordena e sai na exportação.

## Interação com o resto do produto

**Tarefa recorrente.** Os valores **são copiados** para cada ocorrência — eles
descrevem o trabalho, que é o critério do ADR 0010. Editar o valor na tarefa de
origem muda as próximas ocorrências, sem sincronização, como todo o resto do
molde.

**Subtarefa.** Tem as mesmas propriedades da tarefa: elas são do projeto, não
do nível.

**Triagem.** A tarefa que chega pela entrada também tem propriedades, e a
obrigatoriedade vale na criação por qualquer porta.

**Ciclo e módulo.** Sem interação: propriedade descreve a tarefa, não onde ela
está sendo executada.

## Fora de escopo (v1)

| Item                           | Por quê                                                          |
| ------------------------------ | ---------------------------------------------------------------- |
| Tipo pessoa                    | herda o problema do responsável que sai do projeto (ADR 0010 F5) |
| Fórmula e rollup               | fonte de defeito nos quatro concorrentes ao mesmo tempo          |
| Checkbox                       | seleção única com dois valores já é isso, com rótulos melhores   |
| Reuso entre projetos           | é o contexto global do Jira, com o custo que eles mediram        |
| Propriedade por tipo de tarefa | amarra duas decisões independentes                               |
| Espaço público                 | o que é interno não vaza por acidente                            |
