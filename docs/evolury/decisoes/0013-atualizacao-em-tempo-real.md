# ADR 0013 — Atualização do cartão em tempo real

- **Status:** Proposto (17/08/2026)
- **Contexto:** funcionalidade [automacao](../funcionalidades/automacao/especificacao.md)
- **Relacionado:** [ADR 0012](0012-automacoes-personalizadas.md) (automações), [ADR 0011](0011-propriedades-personalizadas.md) (propriedades), [ADR 0010](0010-tarefas-recorrentes.md) (recorrência)

## O problema, medido

Quando uma automação atribui um responsável, o cartão no quadro não muda. O
responsável só aparece depois de recarregar a página. Relatado duas vezes em uso
real.

O que a leitura do código mostrou, e que muda o diagnóstico:

| Fato                                                          | Onde                                                                     |
| ------------------------------------------------------------- | ------------------------------------------------------------------------ |
| a regra roda **depois** da resposta HTTP, no Celery           | por desenho, [ADR 0012](0012-automacoes-personalizadas.md)               |
| ela leva **~24 ms**                                           | `duration_ms` das execuções reais em produção                            |
| não há canal de tempo real nem polling para tarefas           | nenhum `WebSocket`/`EventSource`/`setInterval` em `core/store/issue/`    |
| o quadro **nem revalida ao voltar para a aba**                | `revalidateOnFocus: false, revalidateIfStale: false` nos roots de layout |
| o cliente atualiza o cartão otimisticamente, do que ele mudou | `issueUpdate` grava só as chaves que enviou                              |

O produto **não tem como dizer ao cliente "mudou algo que não foi você"**. A
automação é a primeira funcionalidade que faz exatamente isso — mas não é a
única que sofre: hoje, duas pessoas no mesmo quadro também não se enxergam.

Isto não é o mesmo defeito de [#144](https://github.com/evolury/plane/pull/144).
Lá era chave de cache não invalidada no **mesmo** cliente, que sabia ter salvado.
Aqui a mudança acontece fora do pedido e ninguém avisa.

## Conferido contra o mercado e a literatura (17/08/2026)

### O que os produtos comparáveis fazem

**Linear** mantém cópia local em IndexedDB e recebe _delta packets_ por
WebSocket: o servidor executa a mutação, gera o conjunto de deltas e transmite a
todos os clientes conectados, que aplicam com _last-writer-wins_. É o desenho
mais ambicioso da categoria — e o mais caro: exige motor de sincronização,
bootstrap de estado e resolução de conflito próprios.

**Slack e afins** usam _fan-out_ por corretor (Redis/NATS/Kafka), que desacopla
quem publica de quem recebe e escala horizontalmente.

### A escolha que decide o custo: empurrar o dado ou empurrar o aviso

A literatura de cache é explícita, e a recomendação mais citada é a do autor do
TanStack Query: **invalidação por evento** funciona melhor que empurrar o dado,
porque se o evento chega para uma entidade que ninguém está olhando, nada
acontece — a próxima visita busca de novo. O padrão correspondente aparece
também com SSE + Redis pub/sub: o trabalhador publica um evento de invalidação
ao terminar, e o cliente rebusca, em vez de receber a carga inteira.

Para nós, o argumento decisivo não é banda — é **autorização**:

- **Empurrar o dado** obriga o servidor a decidir, por destinatário, quem pode
  ver cada campo. É uma segunda implementação das regras de permissão, paralela
  à da API, que precisa ficar correta para sempre. Toda divergência entre as
  duas é vazamento.
- **Empurrar o aviso** (`a tarefa X mudou`) faz o cliente rebuscar pela API
  normal, que **já** aplica todas as regras. Quem não pode ver recebe 404 e não
  mostra nada. Nenhuma superfície nova de autorização de dados.

O `live` hoje **não confere participação no projeto**: `onAuthenticate` prova a
identidade (o cookie é do `userId`) e lê `projectId` do parâmetro da URL sem
validar. Para documentos isso é coberto adiante, na busca da página. Um canal de
eventos de tarefa precisaria da checagem explícita — e empurrar só o aviso
reduz o estrago de um erro ali de "vazou o conteúdo" para "vazou que algo mudou".

## Por que o `live`, e não as alternativas

| Caminho                   | Custo                                               | Cobre tudo? | Veredito                                            |
| ------------------------- | --------------------------------------------------- | ----------- | --------------------------------------------------- |
| rebuscar após a escrita   | pequeno                                             | não         | corre com a fila; não cobre mudança de outra pessoa |
| polling curto no quadro   | requisição contínua para todos, inclusive sem regra | sim         | funciona sempre, custa sempre                       |
| **empurrar pelo `live`**  | um canal novo num serviço que já existe             | sim         | **recomendado**                                     |
| motor de sync tipo Linear | IndexedDB, bootstrap, resolução de conflito         | sim         | desproporcional ao problema                         |

O que torna o `live` barato aqui é que a infraestrutura **já está de pé**:

- **WebSocket já atravessa o proxy.** O Caddy roteia `/live/*` para `live:3000`
  e faz o _upgrade_ sozinho. Zero configuração nova de rede.
- **O Redis é o mesmo.** `api` e `live` apontam para `redis://plane-redis:6379/`.
  O `PUBLISH` do Django e o `SUBSCRIBE` do Node não precisam de corretor novo.
- **O `live` já é multi-instância.** Usa `@hocuspocus/extension-redis` para
  espalhar entre réplicas; o mesmo padrão serve ao canal novo.
- **Já tem autenticação por cookie**, `express-ws` e `ioredis` no lugar.

E há **um único ponto de publicação**: a tarefa `issue_activity` é o funil por
onde passam todas as mudanças de tarefa — 124 chamadas em 24 arquivos caem lá. A
publicação entra ao lado de `despachar_atividades`, que já ocupa essa posição.
Um enxerto, não 124.

> Consequência que vale declarar: por estar no funil, o mecanismo cobre **toda**
> mudança, não só as de automação. O mesmo trabalho que corrige o defeito
> relatado entrega o quadro multiusuário — hoje ausente. É ganho, mas também é
> escopo: a implantação deve ser faseada.

## Os cenários — a matriz completa, não uma amostra

As 13 ações do motor, cruzadas com o que o cartão exibe. As colunas do cartão
saem de `ISSUE_DISPLAY_PROPERTIES`; as propriedades personalizadas entram por
`issue-properties`, presente nos blocos de kanban, lista e planilha.

| Ação               | Muda no cartão                             | Tipo de evento          |
| ------------------ | ------------------------------------------ | ----------------------- |
| `set_state`        | estado — e **troca de coluna**             | alterada                |
| `set_priority`     | prioridade — e troca de coluna             | alterada                |
| `set_assignees`    | responsável _(o defeito relatado)_         | alterada                |
| `set_labels`       | etiquetas                                  | alterada                |
| `set_date`         | início / vencimento; posição no calendário | alterada                |
| `set_property`     | propriedade personalizada                  | alterada **+ 2º store** |
| `add_to_cycle`     | ciclo; entra/sai do quadro do ciclo        | alterada + lista        |
| `add_to_module`    | módulo; entra/sai do quadro do módulo      | alterada + lista        |
| `create_subtasks`  | contagem de subtarefas do pai              | alterada + criada       |
| `archive`          | **o cartão some do quadro**                | removida                |
| `create_work_item` | **cartão novo aparece**                    | criada                  |
| `add_comment`      | nada no cartão (só no detalhe)             | alterada _(detalhe)_    |
| `notify`           | nada no cartão (caixa de entrada)          | notificação             |

Três leituras que só a matriz inteira dá:

1. **Não é um tipo de evento, são três.** Seis ações mudam um campo; quatro
   mudam a **participação da tarefa na lista** (arquivar, criar, ciclo, módulo).
   Uma correção que só rebusque a tarefa alterada resolve o caso relatado e
   deixa arquivar e criar quebrados — sem que ninguém perceba, porque o
   responsável, que era o sintoma, passou a funcionar.
2. **`set_property` mexe em dois stores.** O valor da propriedade não vive no
   store de tarefas; é o mesmo caminho separado que o [#144](https://github.com/evolury/plane/pull/144)
   teve de invalidar à parte. Tratar só o store de tarefas deixa a propriedade
   personalizada parada na tela.
3. **A máquina do cliente já existe.** `issueUpdate(..., shouldSync = false)`
   aplica a mudança **sem** escrever de volta, e `updateIssueList(depois, antes)`
   reposiciona a tarefa entre os grupos, corrige as contagens e respeita o filtro
   de subtarefas. É exatamente o que um receptor de evento precisa chamar.

### O ponto que exige cuidado

`updateIssueList` **não** avalia os filtros ricos do quadro. Acrescentar às
cegas uma tarefa recém-criada faria aparecer, no quadro de quem filtrou, um
cartão que o filtro exclui.

Por isso a divisão proposta é assimétrica, e de propósito:

- **campo alterado** → remendo cirúrgico da tarefa (um `GET` de uma tarefa);
- **criada / removida da lista** → rebusca da lista, com _debounce_.

O caso comum — 6 das 13 ações, e o defeito relatado entre elas — fica barato; o
caso raro fica correto.

## Desenho proposto

```
Django (issue_activity, ao lado de despachar_atividades)
   │  PUBLISH  evolury:tarefas  {projeto, tarefa, tipo, ator}
   ▼
Redis (o mesmo de hoje)
   │  SUBSCRIBE
   ▼
live  ─ /live/eventos  (WebSocket, sala por projeto, participação conferida)
   │  {tipo: "alterada", tarefa: "<uuid>"}
   ▼
web   ─ busca a tarefa pela API normal (permissão aplicada lá)
        └─ issueUpdate(..., shouldSync: false) + updateIssueList(depois, antes)
```

O evento carrega **identificadores, nunca conteúdo**. Quem não pode ver a tarefa
recebe 404 da API e não mostra nada.

## Fases

1. **O cano.** Publicação no funil, sala por projeto no `live` com checagem de
   participação, receptor no cliente, apenas `alterada` de campo. Fecha o defeito
   relatado e as 6 ações de campo.
2. **A lista.** `criada` e `removida` com rebusca debounced; ciclo e módulo.
3. **O resto da tela.** Propriedades personalizadas (segundo store), detalhe da
   tarefa, caixa de entrada.

## Verificação

Cada linha da matriz vira teste, e nenhuma fica como "provavelmente funciona":

- **Contrato (`planetest`)**: cada ação publica o evento do tipo certo; ação sem
  efeito **não** publica; quem não participa do projeto não recebe.
- **Injeção de defeito** em cada teste, com a asserção de que a injeção pegou —
  o teto de página já ensinou que suíte verde pode estar medindo o lugar errado.
- **Visual (`planedev`)**, dirigindo o navegador: para as 13 linhas, com **duas
  abas abertas**, a mudança feita pela regra tem de aparecer na segunda aba sem
  recarregar. Arquivar e criar exigem a segunda aba para valer.
- **Carga**: alterar 200 tarefas em lote com 5 regras ativas, medindo publicações
  e rebuscas — o remendo por tarefa não pode virar tempestade de `GET`.

## Medido em produção (17/08/2026, fase 1 implantada)

| Verificação                              | Resultado                                    |
| ---------------------------------------- | -------------------------------------------- |
| canal sem sessão                         | fecha com 1008                               |
| canal para projeto do qual não participo | fecha com 1008                               |
| canal para o meu projeto                 | abre                                         |
| `PATCH` de campo → aviso no canal        | 1 aviso, com `tipo`, `tarefa` e `ator`       |
| automação → aviso com o robô como ator   | **+86 ms depois do meu**, ator = robô        |
| cartão no navegador, sem recarregar      | responsável e prioridade apareceram em < 2 s |

A prova visual foi feita com a aba parada: a mudança entrou pela API de fora do
navegador, e a URL da aba continuou a mesma do início ao fim.

## Limite conhecido da fase 1: duas abas da MESMA pessoa

O cliente ignora o aviso cujo `ator` é ele próprio, para não rebuscar por causa
da mudança que ele mesmo acabou de aplicar. O filtro é por **pessoa**, e não por
conexão — então, se a mesma pessoa está com duas abas abertas e muda algo na
primeira, **a segunda ignora o aviso**.

Isso não afeta o defeito que motivou o ADR: o ator da automação é o robô, e o de
outra pessoa é ela. Mas é o caso que a medição acima quase escondeu — o cartão
atualizou a prioridade que _eu_ tinha mudado, e não por causa do meu aviso: foi a
rebusca disparada pelo aviso da automação que trouxe os dois campos juntos.

A saída é identificar a **conexão**, e não a pessoa, e devolvê-la ao cliente para
ele filtrar por ela. Fica para a fase 2, junto com o resto que mexe em lista.

## Consequências

- **A favor:** cobre toda a matriz; nenhuma infraestrutura nova; nenhuma segunda
  implementação de permissão; entrega o quadro multiusuário de brinde.
- **Contra:** é serviço novo em caminho crítico de tela. Cliente sem WebSocket
  (rede que bloqueia _upgrade_) volta ao comportamento de hoje — degrada, não
  quebra. O `live` passa a ter um segundo motivo de existir, e a checagem de
  participação nasce como código de segurança que precisa de teste próprio.
- **Descartado:** empurrar o conteúdo da tarefa (duplica autorização), polling
  (custo permanente para todos), motor de sync local (desproporcional).

## Fontes

- [Reverse engineering do sync engine do Linear](https://github.com/wzhudev/reverse-linear-sync-engine) — endossado pelo CTO deles
- [tkdodo — WebSockets com React Query](https://tkdodo.eu/blog/using-web-sockets-with-react-query) — invalidação por evento em vez de empurrar o dado
- [Invalidação em tempo real com SSE, Redis e filas](https://armand-salle.fr/post/real-time-cache-invalidation-sse-trpc-redis-bullmq/)
- [WebSocket.org — autenticação](https://websocket.org/guides/authentication/) e [segurança](https://websocket.org/guides/security/)
- [Ably — boas práticas de arquitetura WebSocket](https://ably.com/topic/websocket-architecture-best-practices)
- [Hocuspocus — hooks e mensagens stateless](https://tiptap.dev/docs/hocuspocus/server/hooks)
