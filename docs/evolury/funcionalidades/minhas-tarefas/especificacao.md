# Minhas tarefas — Especificação

- **Status:** aprovada (11/08/2026)
- **Decisões estruturais:** [ADR 0001](../../decisoes/0001-minhas-tarefas-overlay-pessoal.md)

## Objetivo

Uma página pessoal, por workspace, onde o usuário organiza os work items
atribuídos a ele em **etapas próprias** — independentes dos estados dos
projetos — nos moldes do My Tasks do Asana. O item continua pertencendo ao
projeto e ao estado que sempre teve; a etapa é uma camada de organização que só
o dono vê.

## Navegação

- Item **"Minhas tarefas"** na sidebar, imediatamente acima de "Minhas
  atividades" (página `/profile`, renomeada de "Seu trabalho" em 12/08/2026;
  ordem invertida na mesma data a pedido do produto).
- Rota: `/[workspaceSlug]/my-tasks`.
- Acesso: admin e membro do workspace (mesma regra de "Minhas atividades"; guest não
  vê).
- O item aparece no diálogo "Personalizar navegação" como os demais, podendo
  ser ocultado/reordenado.

## Etapas

Espelham a mecânica dos estados de projeto:

- Cada etapa tem **nome**, **cor** e **grupo** (um dos cinco grupos globais:
  backlog, não iniciado, iniciado, concluído, cancelado — triage não é
  elegível).
- A tela de gestão agrupa as etapas por grupo, como em Configurações → Estados
  do projeto: criar, editar, excluir, reordenar por arrasto e marcar a **etapa
  de entrada**.
- Existe exatamente **uma etapa de entrada** por usuário/workspace: é a "primeira
  etapa", onde todo item atribuído aparece até ser movido. O controle se chama
  **"marcar entrada"** na tela — "padrão" não dizia o que a etapa faz, e a linha
  passou a ter várias marcações disputando esse nome.
- Além da entrada, a etapa pode receber **marcações de vencimento** — hoje,
  amanhã, depois, vencidas — e um interruptor de **sem automação**. As duas
  coisas governam a varredura diária descrita abaixo. Ver
  [ADR 0014](../../decisoes/0014-etapas-por-vencimento.md).
- **Todas as marcações da linha têm o mesmo visual**, entrada inclusive, e a
  marcação ativa fica sempre visível: só a desmarcada aparece no hover. Marcação
  é informação, não ação — saber qual etapa recebe as vencidas não pode exigir
  passar o mouse por oito linhas.
- **Os grupos concluído e cancelado não recebem marcação de vencimento nem
  interruptor de automação.** Tarefa concluída ontem está tecnicamente vencida, e
  deixar o controle à mostra ali só oferece uma escolha que a varredura ignora.
- Excluir uma etapa migra os itens associados a ela para a etapa de entrada. Não
  se exclui a etapa de entrada (mesma regra do estado padrão de projeto), nem a
  **última** etapa de um grupo de encerramento — concluir e cancelar procuram o
  destino **dentro do grupo**, e um grupo vazio faria a tarefa concluída cair
  junto das recém-chegadas. Com duas etapas no grupo, as duas podem ser
  excluídas. A regra é do servidor; a tela apenas esconde o ícone onde ele não
  funcionaria.
- A gestão vive na própria página (painel/aba "Etapas"), sem rota de
  configurações separada.

### Seed inicial

No primeiro acesso à página, as etapas são criadas automaticamente para o
usuário naquele workspace:

| Ordem | Nome             | Grupo        | Marcações                    |
| ----- | ---------------- | ------------ | ---------------------------- |
| 1     | Recentes         | não iniciado | entrada · **sem automação**  |
| 2     | Em Andamento     | iniciado     | —                            |
| 3     | Para Hoje (fila) | iniciado     | hoje                         |
| 4     | Pendências       | em espera    | vencidas · **sem automação** |
| 5     | Para amanhã      | em espera    | amanhã                       |
| 6     | Para Depois      | em espera    | depois                       |
| 7     | Concluídas       | concluído    | conclusão                    |
| 8     | Cancelado        | cancelado    | —                            |

**Recentes e Pendências nascem fora da automação**, e não por acaso. Recentes é
onde se toma conhecimento do que chegou — esvaziá-la toda madrugada a impediria
de cumprir esse papel. Pendências costuma receber, à mão, coisa que a pessoa quer
manter à vista mesmo com vencimento futuro.

O seed é ponto de partida, não imposição: tudo é renomeável, recolorível,
excluível e remarcável (exceto a regra da etapa padrão única). Nomes seguem
pt-BR, idioma padrão da instância.

## Conteúdo da página

- **O que entra:** todo work item com o usuário entre os responsáveis, em
  qualquer projeto do workspace ao qual ele tenha acesso.
- **O que não entra:** itens arquivados, rascunhos, itens em triage/intake
  pendente — os mesmos recortes da página "Minhas atividades".
- **Primeira etapa implícita:** item atribuído que nunca foi movido aparece na
  etapa padrão. Não há gravação no momento da atribuição — a associação nasce
  no primeiro movimento.
- **Desatribuição:** o item some da página. Se voltar a ser atribuído, reaparece
  na etapa em que estava (a associação é preservada).
- **Conclusão/cancelamento no projeto:** o item **não** muda de etapa sozinho —
  permanece onde o usuário o deixou, com o estado real visível no card. Filtros
  de exibição permitem ocultar concluídos.

## Layouts e interação

- **Lista** e **kanban**, agrupados **fixamente por etapa** (o agrupamento é a
  identidade da página; não há troca de group_by no v1).
- **Ordem das colunas/grupos**: por grupo global — não iniciado → iniciado →
  backlog → concluído → cancelado (backlog antes de concluído, definição de
  produto de 12/08/2026) — e, dentro de cada grupo, pela ordenação do painel
  de etapas. Quadro, lista e painel compartilham a mesma ordem.
- Arrastar entre colunas/grupos move o item de etapa. Reordenação manual dentro
  da etapa é preservada.
- **Mover de etapa não altera nada no projeto** — nem estado, nem atividade,
  nem notificação ([ADR 0001](../../decisoes/0001-minhas-tarefas-overlay-pessoal.md)).
- Filtros (prioridade, projeto, etiqueta, datas), propriedades de exibição e
  ordenação seguem o padrão da página "Minhas atividades".
- Clique no item abre o peek overview normal; edições feitas ali (estado real,
  responsáveis etc.) seguem o fluxo padrão do produto, com atividade e
  notificações — a exceção de silêncio vale só para o movimento entre etapas.
- Quick actions do card: as mesmas da página de perfil.

## Etapa pela janela do work item (v1.2)

Espelho do recurso do Asana: o responsável altera a etapa pessoal de um item
sem sair do contexto dele.

- No **popover de responsáveis** do work item (peek, página de detalhe e
  dropdowns inline de lista/kanban/planilha/intake/relações), a linha
  **"Você"** ganha um seletor com a etapa atual e todas as etapas do usuário.
- Só aparece para quem **é responsável** pelo item (ao se atribuir, o seletor
  surge em seguida — item nasce na etapa padrão implícita). Linhas de outros
  usuários não mostram nada: cada um vê e altera apenas a própria organização.
- Mudar a etapa ali usa o mesmo `move` da página: pessoal e silencioso
  (ADR 0001).
- A etapa efetiva é buscada sob demanda quando o popover abre (o payload de
  work item fora da página não carrega a anotação).

## Movimentação diária pelo vencimento

Decisão e alternativas descartadas no
[ADR 0014](../../decisoes/0014-etapas-por-vencimento.md). O comportamento:

Toda madrugada, no fuso de cada pessoa, a tarefa vai para a etapa que o
vencimento dela indica:

| Situação da tarefa  | Vai para a etapa marcada como |
| ------------------- | ----------------------------- |
| vencimento < hoje   | vencidas                      |
| vencimento = hoje   | hoje                          |
| vencimento = amanhã | amanhã                        |
| vencimento ≥ D+2    | depois                        |
| **sem vencimento**  | hoje                          |

**Tarefa sem vencimento é tarefa esquecida** — mandá-la para hoje é pô-la na
frente de quem pode decidir. Ela continua sem data: a ausência é o lembrete, e a
automação nunca carimba data nenhuma.

### O que a varredura não toca

- tarefa em grupo **concluído** ou **cancelado**, por trava do motor;
- tarefa numa etapa marcada como **sem automação** — a marcação vale para
  **sair**, nunca para chegar;
- qualquer tarefa cujo balde não tenha etapa marcada. As quatro marcações são
  opcionais, ao contrário da etapa padrão.

### Arrastar para reagendar

Mover a tarefa **à mão** para a etapa de hoje ou de amanhã **muda o vencimento**
para hoje ou amanhã. Os outros destinos não tocam a data: "depois" é intervalo
aberto e "vencidas" é passado — carimbar ali seria inventar informação.

É o único caminho que escreve vencimento, e ele é humano por definição. Gera
histórico e aciona regras como qualquer edição feita na tela.

## Fora de escopo do v1

- Sincronizar etapa ↔ estado real (possível v2 como ação explícita no card).
- Abas criadas/inscritas.
- Layouts planilha, calendário e gantt.
- Seções automáticas por data (estilo "Hoje/Amanhã" calculado).
- Exposição na API pública (`/api/v1`) e no space.
- Compartilhar a organização pessoal com outros usuários.

## Idiomas

Toda string nova entra em `packages/i18n` para os 19 locales, seguindo o
fluxo da skill `translate` (pt-BR como referência de redação).
