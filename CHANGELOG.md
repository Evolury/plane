# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento descrito em [VERSIONING.md](VERSIONING.md).

## [1.5.0] — 2026-08-13

### Cartão de tarefa

- **Marca de conclusão à esquerda do ID**, na lista, no quadro e na planilha.
  Na lista ela convive com a caixa de seleção múltipla, que só surge no hover.
- **Tarefa cancelada ganha aparência própria**: esmaecida como a concluída, mas
  com fundo levemente avermelhado — "não vai ser feita" não é a mesma notícia
  que "foi feita". Vale para qualquer etapa do grupo cancelado, inclusive as
  criadas depois pelo projeto.
- **Não se conclui uma tarefa cancelada**: nem o botão do cabeçalho nem a marca
  do card aparecem. Para voltar atrás existe o seletor de estado, que é onde a
  decisão foi tomada.

## [1.4.0] — 2026-08-13

### Concluir sem abrir a tarefa

- **Marca de conclusão no card**, ao lado do ID, na lista, no quadro e na
  planilha — e em Minhas tarefas, que usa os mesmos blocos. Clicar conclui sem
  abrir a tarefa. O ícone ocupa espaço fixo, como o slot do chevron de
  subtarefas, para que os títulos continuem alinhados de linha a linha; fica
  apagado enquanto a tarefa está aberta e verde quando concluída, na mesma
  linguagem do ícone de estado que a página já usa. Calendário e cronograma
  ficam de fora: os blocos ali são de uma linha só.
- **Botão de concluir no início do cabeçalho da tarefa**, antes dos controles
  de navegação — é a ação principal daquela tela.
- A regra de conclusão (destino, confirmação de subtarefas, significado de
  reabrir) passa a viver em um gancho único, usado pelas duas apresentações.

## [1.3.0] — 2026-08-13

### Concluir tarefa

Botão de concluir nos moldes do Asana, com todas as repercussões desenhadas
antes de escrever código (ADR 0009,
`docs/evolury/decisoes/0009-botao-concluir-tarefa.md`):

- **O botão não é um caminho novo.** Ele dispara a mesma atualização de estado
  que o seletor já fazia, então histórico, webhooks, notificações e contadores
  de ciclo e módulo seguem corretos sem nenhuma adaptação — conferido na
  validação: o ciclo relata a tarefa concluída sem que uma linha de código de
  ciclo tenha sido tocada. O que o botão acrescenta é uma **regra de destino**.
- **Destino configurável por projeto**, na página de Estados, ao lado do
  "Marcar como padrão" e só nos estados do grupo concluído. Sem escolha
  explícita vale o primeiro estado do grupo, e o rótulo mostra isso em vez de
  deixar a resposta invisível. `default_state` não foi reaproveitado: ele
  responde a outra pergunta ("estado dos itens novos").
- **Sem interruptor de automação.** Automação é regra que roda sozinha; isto é
  um botão que a pessoa aperta, e cujo efeito ela obteria pelo seletor.
  Configurável é o destino, não a existência do botão.
- **Confirmação ao concluir tarefa com subtarefas em aberto**, com três saídas:
  cancelar, concluir só a tarefa pai ou concluir tudo junto.
- **Conclusão em massa.** A seleção múltipla já existia inteira no código, mas
  vinha desligada porque a única ação oferecida era uma faixa de upsell da
  edição paga. Agora há ação real: a faixa deu lugar à barra de conclusão.
- **Tarefa concluída fica esmaecida** nos cinco layouts, sempre pelo grupo do
  estado — a mesma fonte que o resto do produto usa.
- **Minhas tarefas** ganha exceção de mão única ao ADR 0001: ao entrar no grupo
  concluído, a associação pessoal de cada responsável vai para a etapa dele de
  concluídas; mover etapa pessoal continua sem alterar nada no projeto.

### Português como idioma único

O produto passa a ter um idioma só (ADR 0004,
`docs/evolury/decisoes/0004-idioma-unico-pt-br.md`):

- 17 idiomas sem uso removidos — 532 arquivos e 7,8 MB a menos —, mantendo o
  inglês como fonte das chaves. O seletor de idioma sai da interface e das
  preferências; a migração 0128 fixa `pt-BR` para quem já tinha outro escolhido.
- Centenas de textos herdados que nunca passavam pelo i18n foram traduzidos,
  incluindo os que só apareciam em telas específicas. Uma varredura sem filtro
  encontrou 238 textos que a primeira auditoria tinha deixado passar.
- `@plane/ui`, `@plane/editor` e `@plane/propel` passam a poder traduzir o texto
  que nasce dentro deles (ADR 0008). A fronteira "pacote sem i18n" existe para
  design system publicado; aqui os pacotes servem a um produto só, e o custo de
  mantê-los mudos era inglês na cara do usuário.
- Grupo `backlog` vira **"Em espera"**; nomes de estado padrão de projetos novos
  nascem em português, com migração dos projetos existentes que ainda usavam os
  nomes em inglês (migração 0127).

### Evotask

A plataforma passa a se chamar **Evotask** em todo o produto — interface,
e-mails, metadados e documentação. Logo e identidade visual ficam para depois.

### Padrões do Brasil

- **Fuso horário fixo e sem escolha por usuário**: só os quatro fusos do Brasil,
  uma opção por offset, nomeada pela cidade principal (migrações 0130 e 0131).
  O Brasil não tem fuso único — daí a lista curta em vez da remoção.
- **Semana começa no domingo**, globalmente e sem opção por usuário
  (migração 0129, ADR 0005).
- **Temas reduzidos a sistema, claro e escuro**, sem alto contraste nem
  personalizado (migração 0132, ADR 0007).

### Correções

- Erro React #418 em produção: os metadados do documento saíam com chaves de
  i18n cruas e o `HydrateFallback` divergia do HTML gerado no build. Duas causas
  distintas, as duas corrigidas.
- Serviço `live` em laço de reinício desde a poda das imagens de produção:
  `intl-messageformat` é peer dependency de `i18next-icu` e sobrevivia por
  hoisting. Passa a ser declarada em `@plane/i18n`, que é quem precisa dela em
  runtime.
- Feed de atividades comparava o verbo contra strings traduzidas, então em
  português o ramo errado sempre vencia — em três lugares.
- Automação de fechamento buscava o estado cancelado **sem filtrar por projeto**
  e podia pegar o de qualquer projeto do banco.
- Alerta fora de contexto ao arrastar tarefa entre etapas de Minhas tarefas.
- Nome do usuário espremido pelo seletor de etapa no popover de responsáveis.

## [1.2.0] — 2026-08-12

### Terminologia "Tarefa"

O work item passa a se chamar **tarefa** em todo o produto em português
(ADR 0003, `docs/evolury/decisoes/0003-terminologia-tarefa-pt-br.md`):

- 559 strings do locale pt-BR renomeadas com revisão de concordância de
  gênero ("nova tarefa", "nenhuma tarefa encontrada", "subtarefa", "tipos
  de tarefa"); demais idiomas mantêm seus termos nativos. Chaves de i18n,
  código, API e banco permanecem `issue`/`work_item` — mudança só na camada
  de tradução.
- ~45 textos herdados do upstream fixos em inglês (feed de atividade,
  modais de confirmação, gráficos de ciclo, tooltips, tour, convites)
  viraram chaves de tradução — 44 chaves novas nos 19 idiomas. Botões do
  modal de exclusão e breadcrumbs de Arquivos/Ciclos/Módulos também
  deixaram de ser fixos em inglês.

### Minhas atividades

- "Seu trabalho" renomeada para **"Minhas atividades"** (sidebar, página
  `/profile`, Power-K e "Personalizar navegação") e reposicionada abaixo de
  "Minhas tarefas". Para preferências já criadas, a migração 0126 troca a
  ordem dos dois itens preservando reordenações manuais.

### Minhas tarefas — etapa pelo popover e ordenação

- Seletor de etapa pessoal no popover de responsáveis (F7, espelho do
  Asana): em qualquer janela do work item, o responsável logado vê e troca
  a própria etapa na linha "Você" — só para si, sem tocar o estado real.
- Etapas ordenadas por grupo global em todo lugar (quadro, lista e painel),
  com backlog antes de concluído; correção do drag no painel que gerava
  sequência fora de ordem.
- Nome do usuário não é mais espremido pelo seletor de etapa no popover de
  responsáveis.

## [1.1.0] — 2026-08-12

### Minhas tarefas

Organização pessoal dos work items atribuídos, nos moldes do My Tasks do
Asana — a primeira funcionalidade própria do produto, documentada de ponta a
ponta em `docs/evolury/funcionalidades/minhas-tarefas/`.

- Página "Minhas tarefas" na sidebar (abaixo de "Seu trabalho"), com comando
  no Power-K (`gt`) e entrada no "Personalizar navegação".
- Etapas pessoais por usuário e workspace, baseadas nos grupos globais: seed
  de 5 no primeiro acesso, painel de gestão (criar, editar, excluir com
  migração para a padrão, reordenar, marcar padrão) reusando a UI de estados
  de projeto.
- Todo item atribuído aparece na etapa padrão até ser movido; mover é
  organização pessoal — não altera o estado real, não gera atividade, webhook
  ou notificação (ADR 0001).
- Layouts lista e kanban com drag entre etapas e ordenação manual pessoal
  (o sort real do item nunca é tocado), filtros ricos, propriedades de
  exibição e empty states ilustrados.
- Backend aditivo: duas tabelas novas, cinco endpoints sempre restritos ao
  próprio usuário, 31 testes de contrato; matriz de compatibilidade com 23
  verificações executada e assinada.

### Melhorias e correções

- Valores dos filtros ricos (prioridade, grupo de estado) traduzidos em todas
  as páginas — antes apareciam em inglês.
- Ilustração pt-BR ("Meus post-its") no empty state dos stickies.
- Correção de contrato na paginação agrupada da nova listagem: resposta vazia
  agora carrega todas as chaves de grupo (antes o front ficava em
  "carregando" eterno).

## [1.0.0] — 2026-08-11

Primeira versão como produto independente. Consolida o trabalho feito sobre o
Plane CE v1.4.1 e corta os vínculos operacionais com o projeto de origem — ver
[UPSTREAM.md](UPSTREAM.md).

### Idioma e padrões brasileiros

- pt-BR passa a ser o idioma padrão da instância, aplicado antes mesmo do login.
- Interface traduzida de ponta a ponta: `apps/web`, `apps/space`, o god-mode
  (`apps/admin`, que não tinha i18n) e o editor, que ganhou tradução via prop.
- Tradução alcançou também o que não estava exposto ao i18n: feed de atividades,
  mensagens de autenticação, modais, empty states, toasts, validações, eixos de
  analytics, filtros de duração, prioridades, categorias de estado e rótulos
  vindos de constantes.
- `translate()` exposto para uso fora de hooks.
- Projetos novos nascem com fuso de Brasília; datas e horários passam a seguir o
  padrão brasileiro em vez do `en-US` do date-fns.

### Marca e interface

- Marca da Evolury no rodapé da barra lateral, com variante clara e escura, no
  lugar do badge de edição do upstream.
- "Star us on GitHub" removido do header.
- "Faturamento e planos" oculto das configurações do workspace.

### Independência do upstream

- Telemetria desligada em todas as camadas: a instância não envia mais métricas
  para `telemetry.plane.so` a cada 6 horas nem a cada start de container, o
  toggle nasce desligado e não há endpoint default no código. Instâncias já
  registradas são desligadas por migration. Detalhes e caminho de volta em
  [docs/telemetria.md](docs/telemetria.md).
- Registro da instância não consulta mais a API do GitHub atrás de releases do
  upstream; a versão em execução vem de `APP_VERSION` ou do `package.json`.
- Canais da Plane removidos da interface (documentação, fórum e "reportar bug"),
  dos metadados do repositório e dos contatos de segurança, conduta e issues.
- Workflows repontados para `main`; os que publicam ou implantam na
  infraestrutura do upstream ficam sem gatilho automático.
- Versionamento próprio a partir de `1.0.0`, desacoplado da numeração do Plane.

### Build

- Imagens de produção de `live` e `space` deixam de copiar o `node_modules`
  hoisted do monorepo e passam a usar `pnpm deploy --prod`: `plane-live` caiu de
  1,65 GB para 866 MB (−48%) e `plane-space` de 1,44 GB para 794 MB (−45%).

### Correções

- Botão "Convidar membro" cortado no menu do workspace.
- Dependência faltante de `t` nos memos de filtro do web.
- Chaves de nome e de descrição de menu do editor separadas.
- Parâmetro de telemetria do formulário de setup deixa de ser ignorado por uma
  expressão que sempre resolvia para verdadeiro.

---

Versões anteriores a esta pertencem ao Plane Community Edition e estão no
histórico do repositório até a tag `v1.4.1`.
