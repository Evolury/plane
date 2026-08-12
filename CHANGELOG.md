# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento descrito em [VERSIONING.md](VERSIONING.md).

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
