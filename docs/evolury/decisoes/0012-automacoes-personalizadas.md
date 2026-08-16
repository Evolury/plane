# ADR 0012 — Automações personalizadas (quando / se / então)

- **Status:** Aceito (16/08/2026)
- **Contexto:** funcionalidade [automacao](../funcionalidades/automacao/especificacao.md)
- **Relacionado:** [ADR 0006](0006-fusos-do-brasil.md) (fuso), [ADR 0009](0009-botao-concluir-tarefa.md) (conclusão), [ADR 0010](0010-tarefas-recorrentes.md) (recorrência), [ADR 0011](0011-propriedades-personalizadas.md) (propriedades)

## Contexto

O menu **Configurações → Execução → Automações** entrega duas caixas de seleção
fixas: arquivar e fechar tarefas paradas há N meses. São dois interruptores, não
um recurso. Não há como um administrador dizer "quando a prioridade virar
urgente, avise o responsável".

O objetivo é comercial: automação é o que separa um gerenciador de tarefas de
uma ferramenta de processo, e é a pergunta que aparece na mesa de venda.

## Conferido contra o mercado e a literatura (16/08/2026)

"Quando / se / então" não é convenção de mercado — é o modelo **ECA
(Event–Condition–Action)** de bancos de dados ativos, dos anos 1990. A literatura
já resolveu a divisão: o evento diz _quando perguntar_, a condição diz _se vale_,
a ação diz _o que fazer_; e **avaliação e execução são camadas separadas de
propósito**. O produto não está inventando um padrão, está implementando um
consolidado — o que justifica cortar tudo que não couber nas três caixas.

| Produto    | Gatilho                       | Condição                         | Ação                                   |
| ---------- | ----------------------------- | -------------------------------- | -------------------------------------- |
| **Jira**   | ~15 tipos + agendado com JQL  | campos, JQL, blocos se/senão     | ~40 ações, ramificação, _smart values_ |
| **Asana**  | eventos + agendado            | "verifique se…", sem aninhamento | várias por regra, até 20 por evento    |
| **monday** | receita pronta "quando/então" | qualificador dentro da receita   | ações encadeáveis                      |
| **Linear** | um gatilho                    | igualdade de campo               | **uma** ação, mesma tarefa             |
| **Notion** | mudança de propriedade        | quase nenhuma                    | editar propriedade, avisar             |

A leitura útil: **Linear é pobre demais** (uma ação, sem condição — vira
brinquedo) e **Jira é rico demais** (_smart values_ são uma linguagem com
depurador próprio). O equilíbrio está em Asana/monday: várias ações, condição
real, **sem** linguagem de expressão.

Três armadilhas aparecem documentadas em todos eles:

1. **Laço infinito.** O Jira precisou de uma caixa "permitir que outra regra
   dispare esta" desligada por padrão _e_ de um teto de dez iterações. A
   recomendação explícita deles é preferir "campo alterado" a "tarefa
   atualizada", porque o gatilho genérico dispara em tudo.
2. **"Por que não rodou?"** É a pergunta número um de suporte, e a resposta em
   todos é o **registro de execuções**. Sem ele, a condição que não casou é
   silenciosa por natureza — ela _deve_ parar sem alarme.
3. **Condição fraca vira regra que pega tudo.**

## Decisão

### O "se" é o filtro do produto, inteiro

A condição é a **mesma árvore JSON** que o quadro manda em `filters`. No quadro
ela pergunta "quais tarefas mostrar?"; aqui, "esta tarefa se encaixa?" — o mesmo
predicado com aridade diferente, avaliado como `Issue.objects.filter(pk=id)`
mais a árvore, e `.exists()`.

Não é economia de linhas: é que filtro e automação **não podem divergir** sobre o
que "prioridade é urgente" quer dizer. Sendo o mesmo componente na tela
(`FiltersRow`) e o mesmo backend (`FiltroComPropriedades`), não têm como. As
propriedades personalizadas do ADR 0011 entram de graça.

### Quatro gatilhos, não quinze

**Tarefa criada**, **campo alterado**, **comentário adicionado**, **em um
horário** (F2). O do meio é parametrizado e sozinho cobre estado, prioridade,
responsável, etiqueta, datas, ciclo, módulo e toda propriedade personalizada —
cinco gatilhos nomeados viraram um, e propriedade nova entra sem código novo.

"Tarefa concluída" não vira gatilho próprio: é _estado → grupo concluído_,
oferecido como receita pronta. **A ergonomia mora no catálogo de receitas, não
no motor.**

Ficam de fora: "tarefa atualizada" genérica (a fonte nº 1 de laço), reação,
voto, anexo, link, relação, arquivamento e requisição web de entrada.

### O "quando" casa por id, nunca por rótulo

O histórico grava o NOME do estado e o nome da propriedade; a regra casa pelo
**id**. Casar por nome funcionaria até alguém renomear uma coluna do quadro — e
aí a regra pararia **em silêncio**, que é o pior defeito possível aqui.

Isso obrigou a uma correção no caminho das propriedades personalizadas, que
gravava `IssueActivity` direto e usava o nome como campo. A gravação passou para
`registrar_atividade_de_propriedade`, com duas chaves para a mesma mudança: o
nome para quem lê o histórico, o id (`property_<uuid>`) para quem casa a regra.

### Doze ações, todas por caminhos que já existem

Estado, prioridade, responsáveis, etiquetas, datas, propriedade personalizada
(F1); comentar, notificar, arquivar, ciclo/módulo (F2); criar tarefa e
subtarefas (F3).

Toda ação monta um pedido parcial e o entrega ao `IssueCreateSerializer` — o
mesmo da tela. Isso garante que a automação obedeça às mesmas regras que uma
pessoa: responsável precisa ser membro com permissão de escrita, etiqueta e
estado precisam ser do próprio projeto. Uma automação que pudesse violar isso
seria porta lateral para gravar estado inválido.

Ficam de fora: requisição web de saída (SSRF numa caixa de texto), ramificação
em tarefas relacionadas, se/senão dentro da regra, espera/atraso, e **linguagem
de expressão**. No lugar das _smart values_, uma lista fechada de variáveis.

### Um enxerto, não 124

Há 124 chamadas de `issue_activity.delay` em 24 arquivos, e todas caem na mesma
tarefa Celery. A automação entra uma linha depois do `bulk_create`, simétrica ao
`notifications.delay` que já estava ali. Nenhum caminho novo escapa por
esquecimento, e o descarte é barato: numa instalação sem automação, o caminho
quente termina num `EXISTS` indexado.

### O robô assina, mas não é a trava

As ações são atribuídas a um **usuário-robô por workspace** (`is_bot`, que já
existe e já é excluído das listas de membros). É honestidade de rastro: hoje o
auto-arquivamento credita `project.created_by_id` — a pessoa que criou o projeto
aparece tendo arquivado tarefas que nunca viu.

Consideramos ignorar todo evento assinado pelo robô, o que tornaria o laço
impossível — e tornaria impossível junto o encadeamento legítimo ("mudou para
Homologação → prioridade alta", seguido de "prioridade alta → avisar"). As travas
são outras quatro, e cada uma cobre o que a outra não cobre:

1. **Teto de profundidade 3** no encadeamento entre regras.
2. **A regra não responde a si mesma** — sem isso, "quando a prioridade mudar →
   mudar a prioridade" seria um laço de um elo só.
3. **Teto de execuções por hora**, que desliga a regra e **grava o motivo**:
   regra que emudece sem explicação é pior do que regra que erra.
4. **Ação sem efeito é descartada e registrada.** É o que evita atividade e
   webhook falsos, e é o que faz um ciclo convergir sozinho — na segunda volta o
   valor já é o esperado, nada é gravado, nenhum evento nasce.

### O registro de execuções nasce junto, não depois

Grava as três metades: executou, parou na condição, falhou. E dentro da que
executou, o que cada ação fez — inclusive "já estava assim". O detalhe carrega
**nomes, não ids**: é uma tela para pessoa ler, e um par de UUIDs ali é tão útil
quanto não ter registro nenhum.

## Consequências

- Filtro e automação compartilham vocabulário e avaliação. Campo novo no filtro
  vira condição de automação sem trabalho.
- A regra sobrevive a renomeações de estado, etiqueta e propriedade.
- Não há encadeamento ilimitado, e não há linguagem de expressão para depurar.
- **Sobreposição declarada com o ADR 0010:** a ação "criar tarefa" (F3) faz algo
  que tarefas recorrentes já fazem melhor para o caso agendado. Ela entrou por
  decisão de produto, com as travas acima e com um aviso na tela quando a
  combinação for "agendada + criar tarefa".
- Uma tarefa Celery nova precisa ser declarada em `CELERY_IMPORTS`. Descoberto
  na verificação visual: sem a declaração, o despacho funciona, a mensagem chega
  à fila e o worker a descarta com "unregistered task" — na tela, uma regra que
  simplesmente não roda.
