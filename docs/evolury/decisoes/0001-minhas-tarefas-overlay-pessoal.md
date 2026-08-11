# ADR 0001 — Minhas tarefas como overlay pessoal

- **Status:** Aceito (11/08/2026)
- **Contexto:** funcionalidade [minhas-tarefas](../funcionalidades/minhas-tarefas/especificacao.md)

## Contexto

O produto precisa de uma página "Minhas tarefas" nos moldes do My Tasks do
Asana: o usuário organiza os work items atribuídos a ele em etapas próprias,
independentes dos projetos. As etapas são criadas como os estados de projeto —
nome, cor e vínculo com um dos cinco grupos globais (`backlog`, `unstarted`,
`started`, `completed`, `cancelled`).

No Plane, todo agrupamento de layout deriva de campo do work item (estado,
prioridade, projeto, etiqueta). Uma etapa pessoal não é campo do item: dois
usuários atribuídos ao mesmo item podem tê-lo em etapas diferentes. Isso força
uma escolha sobre onde a organização pessoal vive e o que ela afeta.

## Decisão

1. **Overlay pessoal, sem efeito no projeto.** Mover um item entre etapas — de
   qualquer grupo para qualquer grupo — grava apenas a associação pessoal.
   Nunca altera o estado real do work item, não gera `issue_activity`, não
   dispara webhook nem notificação.

2. **Associação lazy com etapa padrão implícita.** Atribuição não grava nada:
   item atribuído sem associação pertence implicitamente à etapa padrão (a
   "primeira etapa"). A associação só nasce quando o usuário move o item.

3. **Escopo v1:** somente work items atribuídos ao usuário; layouts lista e
   kanban; agrupamento fixo por etapa.

4. **Modelo de dados aditivo:** duas tabelas novas (`WorkStage`,
   `WorkStageIssue`), escopadas por `workspace + owner`, seguindo o precedente
   de `Sticky`. Nenhuma tabela herdada é alterada.

## Alternativas consideradas

- **Sincronizar estado real** (mover para etapa do grupo "completed" conclui o
  item no projeto): mais poderoso, mas cria efeitos colaterais entre projetos
  (automações de arquivamento, ciclos, notificações aos demais responsáveis) e
  transforma um gesto de organização pessoal em mutação compartilhada.
  Descartado no v1; pode voltar como ação explícita no card (v2).
- **Abas atribuídas/criadas/inscritas** como em "Seu trabalho": semântica
  confusa (etapas para itens em que o usuário é só inscrito?) e escopo maior
  sem ganho claro. Descartado.
- **Etiquetas pessoais** como mecanismo de balde: etiquetas são de workspace e
  visíveis a todos — não são pessoais. Descartado.

## Consequências

- A página é segura por construção: `owner = request.user` em toda a API, sem
  superfície de IDOR.
- O histórico do work item permanece limpo — organização pessoal é invisível
  para os demais.
- Duas fontes de verdade convivem (estado real × etapa pessoal); a
  especificação assume isso abertamente, como o Asana.
- A integração do agrupamento por etapa nos layouts compartilhados é o único
  ponto de risco técnico; a abordagem (fonte de agrupamento aditiva × store
  dedicado com resolução própria) será decidida no spike F0 e registrada no
  ADR 0002.
