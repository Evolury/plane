# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento descrito em [VERSIONING.md](VERSIONING.md).

## [1.29.1] — 2026-08-19

**Patch**: o alvo de exclusão do arrasto deixa de parecer mensagem de erro.

### Na tela

- **Arrastar um cartão não abre mais um alerta vermelho no topo da tela.** A
  caixa "solte aqui para excluir" nascia vermelha e em itálico no instante em
  que qualquer arrasto começava — quem só queria mudar a tarefa de coluna lia
  aquilo como erro. Agora ela é neutra enquanto você arrasta, com um ícone de
  lixeira, e **só fica vermelha quando o cartão está em cima dela**, que é o
  momento em que o aviso tem o que dizer.

- Ao passar por cima, a caixa borrava o próprio texto e parecia quebrada. O
  borrão saiu.

- O rótulo encurtou para "Solte aqui para excluir": o ícone diz o resto, e sem o
  objeto ele para de dizer "a tarefa" no quadro de épicos.

Em "Minhas tarefas" a caixa continua não existindo — ali arrastar é organização
pessoal e nunca toca o item real
([ADR 0001](docs/evolury/decisoes/0001-minhas-tarefas-overlay-pessoal.md)).

## [1.29.0] — 2026-08-19

**Minor**: a **propriedade personalizada vira eixo do quadro** — um projeto só
com vários fluxos, em vez de um projeto por fluxo
([ADR 0011](docs/evolury/decisoes/0011-propriedades-personalizadas.md)).

### Na tela

- **Arrastar o cartão entre as colunas muda o valor da propriedade.** No quadro
  e na lista; soltar em "Nenhum" apaga. Era o gesto que faltava: dava para ver o
  fluxo e filtrar por ele, mas mudar o valor exigia abrir a tarefa. A mudança
  entra no histórico e aciona as automações, como qualquer edição feita na tela.

- **Subagrupar por propriedade.** O menu passou a oferecer as mesmas
  propriedades do "Agrupar por" — o servidor já sabia responder desde a
  v1.13.0, só o menu não oferecia. Quadro por estado com raias por "Canal",
  por exemplo.

- **"Usar em agrupamentos" na definição da propriedade.** Seleção única já
  aparecia automaticamente nos menus de agrupar; agora é escolha, e a caixa
  **nasce marcada**. É diferente de "mostrar no cartão" pelo custo de cada uma:
  uma pastilha a mais disputa a largura do cartão com todas as outras, um
  agrupamento a mais é uma linha num menu que só quem abre vê.

- **Cada módulo com o próprio fluxo.** Como o módulo guarda o agrupamento dele,
  o de aquisição pode ficar por "Canal" e o de entrega por outra propriedade —
  no mesmo projeto, ao mesmo tempo. É o que dispensa criar um projeto para cada
  conjunto de etapas.

- "Nenhum" voltou a ser a última linha do menu de subagrupar. As propriedades
  entravam depois dela e empurravam a opção de desligar para o meio da lista.

### Por dentro

- Desmarcar "usar em agrupamentos" **não é sugestão de tela**: a marca entrou na
  mesma função que a allowlist do paginador consulta (GHSA-wwgj-929g-42cm), então
  o pedido é recusado com 400 venha da tela, de uma URL colada ou de um script.

- A migração liga a marca em todas as propriedades que já existiam — nenhum
  agrupamento em uso desaparece de um menu sem ninguém ter pedido.

- Seleção múltipla continua sem agrupar: duplicaria o cartão entre colunas, como
  etiqueta, e aí arrastar não teria resposta certa — acrescenta ou substitui?

- Conhecido: cartão movido em **outra aba** atualiza a pastilha na hora, mas só
  troca de coluna ao recarregar. Registrado no
  [backlog técnico](docs/evolury/backlog-tecnico.md).

## [1.28.0] — 2026-08-19

**Minor**: uma tarefa passa a ter **um** responsável, e nunca mais de um
([ADR 0016](docs/evolury/decisoes/0016-um-responsavel-por-tarefa.md)).

### Na tela

- **Um responsável, e a garantia é do banco.** Escolher alguém substitui quem
  estava — é o que um seletor de valor único faz, e o que arrastar entre colunas
  do quadro já fazia. Dois responsáveis deixam de ser possíveis: um índice no
  Postgres recusa, valha o pedido pela tela, pela API ou por importação.

- **A etapa de "Minhas tarefas" saiu de dentro da janela de escolha de pessoas**
  e foi para o lado do nome, na própria tarefa. Ela morava na linha "Você" da
  lista de responsáveis — lugar onde ninguém procura mudar etapa, e que só
  existia porque a lista podia ter várias pessoas.

- **Nome de exibição aceita espaço.** "Tássio Câmara" era recusado com uma
  mensagem que nunca mencionava espaço, e por isso parecia que o problema era o
  acento. Não era: o acento sempre passou. A mensagem passou a dizer o que a
  regra exige.

- Os rótulos de responsável ficaram no singular, e o botão de criar estado
  falava inglês.

### Por dentro

- **Nenhuma migração era executada por CI.** A suíte roda com `--nomigrations`,
  e nenhum workflow subia banco: 24 migrações próprias entraram sem que uma
  única fosse executada fora do deploy. Agora um workflow sobe Postgres, aplica
  a cadeia do zero e recusa modelo alterado sem migração correspondente.

- Ao receber mais de um responsável, fica o último — e a resposta devolve o
  valor efetivo, para que quem integra veja a diferença. O histórico da tarefa
  passou a ler o banco em vez do pedido: antes anunciava duas pessoas quando só
  uma era gravada.

## [1.27.0] — 2026-08-19

**Minor**: **Minhas tarefas** ganha páginas. Criadas fora de qualquer projeto,
com abas no topo para alternar, compartilháveis com pessoas escolhidas e
movíveis para dentro e para fora de projeto
([ADR 0015](docs/evolury/decisoes/0015-paginas-pessoais.md)).

### Na tela

- **Escrever sem escolher projeto.** Nota de reunião, rascunho, checklist que
  ainda não pertence a lugar nenhum: a página nasce sua, em Minhas tarefas.
  Escolher um projeto só para ter onde escrever era uma decisão tomada no pior
  momento — e que depois ninguém desfazia.

- **Abas no topo: Tarefas, Páginas e Compartilhado comigo**, no mesmo desenho
  das abas dos projetos.

- **Compartilhar com quem você escolher**, e com o papel que você escolher:
  **pode ler** ou **pode editar**, pessoa por pessoa. Quem recebe encontra a
  página numa aba própria — a aba Páginas continua sendo só o que é seu.

- **Só o dono compartilha**, mesmo quem recebeu "pode editar". Sem isso,
  "compartilhei com uma pessoa" viraria "compartilhei com quem ela quiser".

- **Mover entre o pessoal e um projeto, nos dois sentidos.** Rascunhar aqui e
  publicar lá, ou recolher de volta. Ao mover para um projeto os
  compartilhamentos caem, porque lá quem manda é o projeto — a tela avisa antes,
  dizendo quantas pessoas perdem acesso.

- **O editor da página passou a falar português.** Ele nunca tinha estado
  traduzido: o editor de documento não montava o provedor de tradução, e todo
  texto dentro dele caía no inglês de reserva. "Sem título", "Digite '/' para ver
  os comandos...", a barra de ferramentas inteira.

### Correções

- **Criar página em um projeto caía no erro genérico.** A tela estava quebrada
  havia oito dias. Era uma variável usada antes de declarada — o `t()` da
  tradução lido dentro de um `useMemo` que roda antes da linha que o cria.

- **Etapas de Minhas tarefas**: o modal de exclusão estava em inglês; o ícone de
  excluir sumiu de Recentes, Concluído e Cancelado, onde não funcionaria; não se
  exclui mais a **última** etapa de um grupo de encerramento, porque concluir
  procura o destino dentro do grupo e um grupo vazio faria a tarefa concluída
  cair junto das recém-chegadas; "marcar padrão" virou **"marcar entrada"**, com
  o mesmo visual das outras marcações e sempre visível.

### Por dentro

- **O teto de avisos do lint não segurava nada**: o `apps/web` declarava 11957
  com 814 avisos reais. É por isso que o aviso que denunciava o defeito da
  criação de página nunca derrubou a CI. Todos os tetos passaram a ser o número
  real, e um aviso novo agora derruba a build.

- **`no-use-before-define` ligada**, com 152 das 180 ocorrências corrigidas de
  verdade: arrow de escopo de módulo virou declaração de função — que é içada, e
  aí a zona morta deixa de existir, não só o aviso.

## [1.26.0] — 2026-08-18

**Minor**: as etapas de **Minhas tarefas** passam a se organizar sozinhas pelo
vencimento. Toda madrugada, cada tarefa vai para a etapa que a data dela indica —
e arrastar entre as etapas de curto prazo passa a ser a forma de reagendar
([ADR 0014](docs/evolury/decisoes/0014-etapas-por-vencimento.md)).

### Na tela

- **A faxina diária deixou de ser sua.** Puxar o que venceu, trazer o que é de
  hoje, empurrar o que ficou para depois: a data já dizia tudo isso, e agora o
  produto faz a conta. Na virada do dia, no seu fuso, cada tarefa vai para a
  etapa marcada como vencidas, hoje, amanhã ou depois.

- **Arrastar para "hoje" ou "amanhã" reagenda a tarefa.** É o que faz etapa e
  data concordarem: sem isso, você moveria a tarefa e a madrugada a puxaria de
  volta. Arrastar para as outras etapas não mexe na data — "depois" é um
  intervalo aberto e "vencidas" é passado.

- **Você escolhe quais etapas recebem cada grupo**, na própria linha da etapa,
  como já se marca a etapa padrão. As marcações são **opcionais**: um grupo sem
  etapa marcada simplesmente não move ninguém. Uma etapa pode receber mais de um
  grupo.

- **Você pode tirar uma etapa da organização automática.** Vale para **sair**:
  o que está ali não é levado embora, mas continua podendo chegar. É o que
  permite "Pendências" receber as vencidas e, ao mesmo tempo, segurar o que você
  põe ali à mão.

- **Tarefa sem data vai para "hoje" — e continua sem data.** Tarefa sem
  vencimento é tarefa esquecida; trazê-la para hoje é pô-la na sua frente. A
  data continua vazia de propósito: é ela que faz você notar.

- **Conta nova já nasce organizada**, com as oito etapas do padrão e as
  marcações prontas. Recentes e Pendências nascem fora da organização
  automática: a primeira é onde se vê o que chegou, a segunda costuma guardar o
  que você quer manter à vista.

### O que a organização automática não toca

Tarefa concluída ou cancelada, por regra do próprio motor — uma tarefa
terminada ontem está tecnicamente vencida, e trazê-la de volta seria
ressuscitar trabalho pronto.

## [1.25.0] — 2026-08-18

**Minor**: a tela inteira passa a acompanhar o que muda de fora. Fecha o
[ADR 0013](docs/evolury/decisoes/0013-atualizacao-em-tempo-real.md), incluindo o
que a versão 1.23.0 tinha deixado de fora sem dizer.

### Na tela

- **Tarefa aberta por link direto agora acompanha.** Quem abre uma tarefa pelo
  endereço dela — de um link colado num chat, por exemplo — via uma página
  parada no tempo: nenhuma mudança feita por outra pessoa, ou por automação,
  chegava até recarregar. O painel que abre sobre o quadro já funcionava; a
  página própria, não.

- **A caixa de entrada avisa sozinha.** O sino só conferia ao abrir a tela: uma
  notificação que chegasse com o produto aberto ficava invisível até alguém
  recarregar ou navegar. É o mesmo atraso do cartão, num lugar em que incomoda
  mais — notificação é justamente o que existe para avisar.

### Por dentro

- A conexão com o serviço de tempo real virou peça única, usada pelo quadro,
  pela página de tarefa e pela caixa. Antes de existir, o quadro era o único a
  tê-la; duplicá-la nas outras duas telas duplicaria também a chance de uma
  cópia envelhecer sozinha.

- Notificação é de uma **pessoa**, e não de um projeto — o sino aparece em
  telas que não têm quadro nenhum. Por isso o canal passou a aceitar conexão
  sem projeto, e toda conexão entra também na sala da própria pessoa. O aviso
  que chega ao navegador não diz quem mais foi avisado.

## [1.24.0] — 2026-08-18

**Minor**: três promessas que o produto fazia e não cumpria, todas em silêncio.
Nenhuma aparecia na tela; todas só acumulavam.

### Na tela

- **A caixa "notificar por e-mail" prometia um envio que não acontecia.** Ela
  vinha marcada por padrão, e numa instância sem servidor de e-mail configurado
  a mensagem era enfileirada para nunca sair — sem erro, sem aviso. Agora ela
  segue a configuração da instância: sem e-mail configurado nasce desmarcada e a
  tela diz por quê, e **volta a nascer marcada sozinha** no dia em que o e-mail
  for configurado.

### Segurança e integridade

- **A fila de e-mail crescia para sempre.** A limpeza automática apagava
  registros pela data de envio — e o que nunca foi enviado não tem data, então
  nunca era alcançado. Bastava o servidor de e-mail estar indisponível, ou não
  configurado, para a tabela crescer sem fim. A limpeza passa a considerar a
  idade do registro, tenha ele saído ou não.

- **Escrita com nome de campo errado respondia "deu certo".** `assignees` no
  lugar de `assignee_ids` — e o mesmo para etiquetas — era descartado em
  silêncio: a resposta dizia sucesso e nada mudava. Agora a recusa é explícita e
  diz o nome certo. Campo extra desconhecido continua sendo ignorado, como
  antes: a recusa vale só para os pares que se confundem.

### Por dentro

- Triagem de seis alertas de redirecionamento aberto que o CodeQL abriu nas
  telas de autenticação — **todos falsos positivos**, com três camadas de
  proteção medidas contra a produção e trancadas por 36 testes.

## [1.23.0] — 2026-08-18

**Minor**: fecha o [ADR 0013](docs/evolury/decisoes/0013-atualizacao-em-tempo-real.md).
O valor de propriedade personalizada marcada para o cartão passa a aparecer sem
recarregar a página, mesmo quando quem gravou foi outra pessoa — ou uma
automação.

### Na tela

- **Valor de propriedade personalizada agora acompanha.** O cartão lê esse valor
  de um endereço próprio, do projeto inteiro, e não junto com o resto da tarefa.
  Era o único dado do cartão que as versões 1.21 e 1.22 ainda não alcançavam:
  buscar a tarefa de novo não o trazia. Vale para a ação **definir propriedade**
  das automações e para quem preenche o campo em outra tela.

### Por dentro

- A gravação de valor **não passa** pelo funil por onde passam as outras
  mudanças de tarefa — ela escreve o histórico direto. Por isso precisou do
  próprio aviso, num só lugar que cobre os dois caminhos que gravam valor: a
  tela e a automação.

- Uma injeção de defeito revelou lacuna nos testes desta funcionalidade: eles
  provavam que o aviso **sabe sair**, não que **é disparado de onde precisa** —
  apagar a chamada deixava a suíte verde. Entrou um teste que percorre o caminho
  real.

## [1.22.0] — 2026-08-18

**Minor**: o quadro passa a acompanhar tudo que muda de fora — inclusive de
outra aba sua, inclusive tarefa que nasce ou some. É a fase 2 do
[ADR 0013](docs/evolury/decisoes/0013-atualizacao-em-tempo-real.md), e fecha o
que a 1.21.0 deixou pela metade.

### Na tela

- **Duas abas suas agora se enxergam.** Na versão anterior, o quadro ignorava
  qualquer aviso cujo autor fosse você — o que confundia "fui eu nesta aba" com
  "fui eu na outra aba". Mudar uma tarefa no notebook não atualizava o desktop
  ao lado. Agora cada aba reconhece só o próprio eco.

- **Tarefa criada de fora aparece, e tarefa arquivada ou excluída some.** Uma
  regra que arquiva deixava o cartão na tela até alguém recarregar; uma
  automação que cria subtarefas não mostrava nenhuma delas. Vale também para
  tarefa criada por outra pessoa no mesmo quadro.

  Sair do quadro é imediato. Entrar rebusca a lista, e isso é de propósito: o
  cartão novo precisa passar pelos filtros do seu quadro, e só o servidor sabe
  responder isso — acrescentar direto faria aparecer, para quem filtrou, um
  cartão que o filtro exclui.

### Por dentro

- O reconhecimento do próprio eco **não** exigiu o servidor identificar a
  conexão, que obrigaria a arrastar um parâmetro novo pelas 124 chamadas do
  funil de histórico. A aba já sabe o que escreveu: ela anota, e a anotação vale
  uma vez e vence em 15 segundos. Valer uma vez é o que mantém a mesma pessoa
  editando a mesma tarefa em duas abas; vencer evita que uma escrita sem
  resposta engula para sempre o próximo aviso daquela tarefa.

- Arquivar e editar chegam ao servidor com o mesmo tipo de atividade — só o
  campo os distingue —, então o aviso passou a ser decidido lendo as linhas de
  histórico, e não só o tipo.

## [1.21.0] — 2026-08-17

**Minor**: o cartão do quadro passa a se atualizar sozinho quando a mudança vem
de fora — de uma automação ou de outra pessoa. É a fase 1 do
[ADR 0013](docs/evolury/decisoes/0013-atualizacao-em-tempo-real.md).

### Na tela

- **O cartão não mudava quando a automação mexia na tarefa.** Uma regra que
  atribuía o responsável só aparecia depois de recarregar a página. A causa não
  era a automação: o produto não tinha como dizer ao cliente "mudou algo que não
  foi você" — o quadro atualiza o cartão do que **ele mesmo** mandou, e não
  revalida nem ao voltar para a aba. Agora o servidor avisa, pelo serviço
  `live`, e o cartão se atualiza em menos de dois segundos.

  Vale para as seis ações de campo — estado, prioridade, responsável, etiquetas,
  datas, ciclo e módulo — nos quadros de projeto, ciclo, módulo e visão. Tarefa
  criada e arquivada mudam a **participação** da tarefa na lista e precisam de
  tratamento próprio: ficam para a fase 2.

  Um limite conhecido: duas abas da **mesma** pessoa ainda não se enxergam. O
  filtro do próprio eco é por pessoa, não por conexão.

- **O aviso da automação vinha em inglês.** O cartão da caixa de entrada exibia
  "Automação created automation em …" num produto em português — o campo
  `automation` não existe no upstream, então a frase caía no renderizador
  genérico, que concatena o verbo com o nome do campo sem traduzir.

### Segurança

- **Notificação sem histórico derrubava a caixa de entrada inteira.** A correção
  anterior pôs a leitura opcional num campo e deixou os três irmãos, o que só
  mudou qual linha estourava.

- **Os parâmetros do canal de eventos iam crus para o caminho da requisição.**
  Achado pelo CodeQL (`js/request-forgery`, crítico) no próprio PR: com um id de
  projeto em forma de travessia, a pergunta "esta pessoa participa do projeto?"
  batia noutro endereço, que responde sim para qualquer sessão. A forma dos dois
  parâmetros passa a ser validada antes de qualquer requisição sair.

### Por dentro

- O aviso carrega **identificadores, nunca conteúdo**: quem recebe busca a
  tarefa pela API normal, que já aplica todas as permissões. Mandar o dado
  obrigaria o servidor a manter uma segunda implementação das regras de
  permissão, e toda divergência entre as duas seria vazamento.

- A publicação entra no funil por onde passam todas as mudanças de tarefa — um
  enxerto, não 124 —, e nenhuma infraestrutura nova foi necessária: o proxy já
  roteia `/live/*` e a API e o `live` já compartilham o mesmo Redis.

## [1.20.0] — 2026-08-17

**Minor**: duas mudanças que se veem na tela — o operador dos filtros passa a
falar português e o cartão passa a atualizar sozinho — junto de três correções
de segurança e do fim da revisão do upstream.

O incremento é minor pelo que se vê, e não pelas correções de segurança: elas
sozinhas subiriam patch, e nenhuma exige ação de quem opera.

### Na tela

- **O operador dos filtros estava em inglês, sem caminho de tradução.** `is`,
  `is any of` e `between` eram texto escrito dentro de `@plane/constants` — um
  pacote sem acesso ao tradutor. Não havia como traduzi-los em tela nenhuma:
  filtros do quadro, das visões, da exportação e o cartão de condição da
  automação. Onde se lia "Prioridade is Urgente" agora se lê **"Prioridade é
  Urgente"**.

- **Valor de propriedade marcado para o cartão só aparecia ao recarregar.** O
  cartão lê de um endereço próprio, do projeto inteiro, e o painel da tarefa
  revalidava só o dele. Eram duas perguntas sobre o mesmo dado, e salvar
  respondia uma. Vale também para ligar e desligar "mostrar no cartão".

- **A criação rápida engolia o motivo da recusa.** Falhava com "Ocorreu algum
  erro" enquanto o servidor mandava a frase — "Preencha: Local." A leitura da
  recusa virou uma função só, porque a API responde em quatro formatos conforme
  quem recusou.

- **Propriedade de seleção recusava o próprio formato que a tela publica.** O
  tipo é `string | string[]`; o multi-select aceitava os dois e o select simples
  não, respondendo com uma frase que não explicava nada. De quebra, a
  conferência e a gravação discordavam — a primeira aceitava a lista e a segunda
  recusava, depois de a tarefa já existir.

### Segurança

Fim da revisão do upstream de 17/08: as cinco branches `secur-*` foram medidas
contra a nossa base, e as duas que faltavam renderam três falhas reais.

- **Login por senha não tinha freio de força bruta.** As quatro views de senha
  estendem `django.views.View`, e o freio do DRF só roda dentro de
  `APIView.initial()` — nunca correu nelas. O link mágico e a recuperação de
  senha já tinham; o alvo óbvio de adivinhação, não. Medido: **30 tentativas
  seguidas sem bloqueio**. Agora a 11ª é recusada.

- **O cliente reescrevia quem criou o projeto.** `created_by` e `updated_by`
  entravam como escrevíveis, e o `save()` só protege `created_by` na criação —
  num `PATCH` o valor do cliente ficava. Campo de auditoria existe para
  responder "quem fez isso"; reescrevê-lo apaga a única coisa que ele serve para
  responder.

- **O cursor decidia o tamanho da página, sem teto.** `per_page` era limitado, o
  `cursor.value` não — e nos paginadores agrupados era ele quem mandava. Medido:
  `per_page=3` com `cursor=100` devolvia 30 linhas.

- **`per_page` zero ou negativo respondia 500.** Erro de parâmetro que o cliente
  lê como falha do servidor e reenvia.

### Por dentro

- **Os testes de JavaScript não rodavam em lugar nenhum.** A CI conferia
  formato, lint, tipos e build — nunca `test`. A suíte do Live, que inclui o
  guarda de SSRF do renderizador de PDF, existia e ninguém a executava; e ela
  nem era executável fora da máquina do desenvolvedor. Agora roda na CI e na
  verificação local, e o `apps/web` ganhou runner com regressão dos dois
  defeitos de interface acima.

- Três linhas da matriz de compatibilidade das automações saíram de "provado por
  leitura" para "provado por execução" — as que afirmavam uma **ausência**, que
  são as que envelhecem pior sem teste.

- O servidor de desenvolvimento abre na rede local por variável (`DEV_HOST`), e
  não por argumento: o turbo não repassa argumento para a tarefa, então a
  instrução antiga não funcionava.

## [1.19.0] — 2026-08-17

**Minor**: duas telas que calavam voltam a falar — a seção de condição das
automações, que era o motivo de nenhuma regra conseguir ter condição, e a
criação rápida de tarefa, que escondia o motivo da recusa. Entram também cinco
correções de segurança encontradas na revisão do upstream.

O incremento é minor pelo que se vê na tela, não pelas correções de segurança:
elas sozinhas subiriam patch, e nenhuma delas exige ação de quem opera.

### Automações

- **O cartão "SE" abria sem nada dentro.** Clicar em "+ Restringir a quais
  tarefas" revelava a frase de ajuda e mais nada: o botão para acrescentar o
  primeiro filtro não estava escondido nem desabilitado — não existia no DOM.
  Na prática, nenhuma regra nova conseguia ter condição.

  A linha de filtros inteira vive dentro de um `<Transition>` cuja visibilidade
  padrão é "tem filtro ativo?". No quadro isso está certo, porque quem revela a
  linha é o botão "Filtros" do cabeçalho. No editor de automação esse botão não
  existe: a linha **é** a interface. Os três consumidores originais dessa
  variante — formulário de visão de projeto, de workspace e o de exportação —
  todos passam `showOnMount`; o cartão de condição era o único que não passava.

- **Rótulo em inglês no botão de filtros.** Era a string `"Filters"` escrita no
  meio do código. Passa despercebida no quadro, onde essa variante quase não
  aparece; no cartão de condição é o botão principal. Passou a usar a tradução
  que já existia, e vale para os quatro lugares que usam a variante.

### Tarefas

- **A criação rápida engolia a frase que o servidor mandou.** Criar tarefa pela
  linha de criação rápida falhava com "Ocorreu algum erro. Por favor, tente
  novamente." A API dizia o que era — quando falta propriedade obrigatória, ela
  recusa com `{"property_values": "Preencha: Local."}` —, mas a tela procurava
  um campo que não existe nessa resposta.

  Doía mais nesse caso porque a criação rápida **não tem** formulário de
  propriedades: quem esbarrava na obrigatória não tinha como preenchê-la ali nem
  como descobrir que era disso que se tratava. O modal completo já tratava bem,
  e era esse contraste que mantinha o problema invisível.

  A leitura da recusa virou uma função só, porque a API responde em formatos
  diferentes conforme quem recusou: `property_values` nos nossos endpoints,
  `error` na app API, `detail` no DRF e `{campo: ["frase"]}` na validação de
  campo. Cada ponto da tela adivinhava um e errava nos outros.

  > **Nota de uso, não de código:** automação **não** preenche propriedade
  > obrigatória na criação. O portão da obrigatória roda antes de a tarefa
  > existir; a regra `work_item_created` roda depois (ADR 0011). Com esta
  > correção a tela passa a dizer qual propriedade falta, em vez de calar.

### Segurança

Cinco falhas encontradas na revisão do upstream de 17/08/2026. Nenhuma vinha de
release nova nem de aviso publicado: saíram de **branches `secur-*` abertas** no
repositório do Plane CE, com correções ainda não mescladas nem divulgadas.

Em todas, o método foi medir antes de corrigir — uma sonda reproduz o ataque
contra a nossa base e imprime o que passou. Foi isso que evitou exagerar (várias
leituras que pareciam vazar devolviam lista vazia) e impediu subestimar: o aviso
citava uma rota, e havia dezoito com a mesma forma.

- **`/convert-document/` do Live não exigia autenticação.** A rota ficava aberta
  a qualquer um. Passou a exigir a chave de servidor, que a API já tinha.

- **SSRF no renderizador de PDF.** O `src` de uma imagem vem do conteúdo da
  página, e o `@react-pdf/image` busca o que receber: nome de serviço da rede
  interna do Docker, endereço de metadados da nuvem, ou um caminho de disco, que
  o pacote entrega ao `fs.readFile`. Os dois nós de imagem estavam expostos — o
  segundo tinha um teste `startsWith("http")`, que não protege nada.

  O guarda novo falha fechado e espelha o guarda Python que já existia, com
  teste comparando as duas listas de faixas bloqueadas. Ele julga IPv6 pela
  forma canônica: `::1` se escreve de muitas maneiras.

- **Rotas de escrita caíam no CRUD genérico do DRF.** Os arquivos de URL da app
  API mapeavam `"put": "update"` em treze lugares, e nenhum viewset da app API
  define `update`. O verbo caía no mixin do DRF, que não sabe nada de papéis,
  sob apenas `IsAuthenticated`. Medido: um membro do workspace, de fora do
  projeto, renomeava módulo e tarefa alheios, publicava visão e editava a caixa
  de entrada de projeto do qual não participa.

  Os treze mapeamentos saíram, e mais dois `PATCH` que apontavam para handler
  inexistente. Nenhum cliente usava: os dois únicos métodos PUT do frontend eram
  código morto. As ações de escrita que são intencionais ganharam o guarda das
  irmãs.

  > **Para quem integra pela app API:** `PUT` nessas rotas passa a responder 405. Use `PATCH`, que é o que o nosso frontend sempre usou. A API pública
  > (`/api/v1/`) não tinha nenhuma rota PUT e não mudou.

- **Criar dentro de um projeto exigia só ser do workspace.** No ramo do `POST`
  das classes de permissão, a consulta era `WorkspaceMember` e nunca
  `ProjectMember` com `project_id`. Medido: um membro do workspace publicava o
  quadro de um projeto alheio **na web** e arquivava projeto alheio. O atalho de
  workspace passa a valer só quando não há projeto na URL — que é o caso de
  criar projeto, onde ainda não existe participação a consultar.

- **A tarefa da URL não precisava ser do projeto da URL.** As rotas de
  sub-recurso trazem projeto e tarefa no caminho, e nada amarrava um ao outro.
  Medido, como membro do projeto A apontando para uma tarefa do projeto B:
  comentário, link, reação, inscrição e relação criados na tarefa alheia,
  relação alheia apagada, e a lista de subtarefas devolvida na íntegra — nas
  duas APIs. A regra passou para um mixin das classes base, porque é uma só.

### Processo

- **A revisão do upstream tinha um defeito próprio.** O passo que lista releases
  novas usava `git tag --list 'v*'`, que desde a nossa bifurcação mistura as
  nossas tags com as deles — e listou as nossas 1.x como se fossem releases do
  upstream a revisar. Trocado por consulta ao remoto.

- Histórico da revisão registrado, incluindo as duas divergências deliberadas do
  caminho do upstream e a branch `secur-236` que ficou de fora, nomeada como
  pendência em vez de silêncio.

## [1.18.1] — 2026-08-16

**Patch**: correção de segurança nas dependências. Nada muda na tela.

### Segurança

- **Fechados os 21 alertas de dependência** abertos — que são 7 avisos em 5
  pacotes: o contador multiplica por manifesto, e o Django aparecia cinco vezes
  por aviso.
  - `django` 5.2.15 → **5.2.16** (3 avisos)
  - `react-router` 7.18.1 → **7.18.2**
  - `nanoid` 3.3.8 → **3.3.18**
  - `js-yaml` 4.3.0 → **4.3.1**
  - `brace-expansion` 5.0.7 → **5.0.9** (só desenvolvimento)

  Os três do Django foram conferidos no nosso código, porque é o framework que
  atende produção: **nenhum dos três caminhos existe aqui** — não há middleware
  de cache do Django, GeoDjango não é usado, e o validador de domínio não é
  chamado diretamente. Corrigidos assim mesmo: "não tem caminho hoje" é uma
  afirmação sobre o código de hoje.

  Triagem completa em
  [historico-de-revisoes.md](docs/evolury/processos/historico-de-revisoes.md).

## [1.18.0] — 2026-08-16

**Minor**: chega funcionalidade nova de verdade a quem usa o produto — a maior
desde o começo do fork, e a que mais pesa comercialmente.

### Automações personalizadas

O menu **Configurações → Execução → Automações** entregava duas caixas fixas:
arquivar e fechar tarefas paradas. Dois interruptores, não um recurso. Agora o
time escreve as próprias regras, no formato **quando / se / então**.

- **Quatro gatilhos**: tarefa criada, campo alterado, alguém comentar, e em um
  horário. O do meio é parametrizado e sozinho cobre estado, prioridade,
  responsável, etiqueta, datas, ciclo, módulo e **toda propriedade
  personalizada do projeto**.
- **A condição é a mesma linha de filtros do quadro.** Tudo que você filtra na
  tela, filtra na regra — inclusive as propriedades personalizadas. Não é
  economia de código: é a garantia de que filtro e automação nunca discordem
  sobre o que "prioridade é urgente" quer dizer.
- **Doze ações**: mudar estado, prioridade, responsáveis, etiquetas e datas;
  preencher propriedade; comentar; notificar (no sino e por e-mail); arquivar;
  incluir no ciclo ativo ou num módulo; criar tarefa e criar subtarefas.
- **Registro de execuções** por regra, que responde "por que não rodou?" —
  inclusive quando a resposta é "a condição não casou" ou "já estava assim".
- **Seis receitas prontas** no estado vazio, que abrem o editor preenchido.
- As mudanças feitas por uma regra aparecem no histórico creditadas a
  **Automação**, e não a você nem a quem criou o projeto.

**A fronteira com Tarefas recorrentes é de propósito, não de sobreposição**: a
agenda cuida da rotina, o evento cuida da reação. Criar tarefa por horário é
trabalho das recorrentes, e a combinação é recusada com uma frase que aponta
para lá. Ocorrência de recorrência não dispara regra de "tarefa criada", a menos
que a regra peça.

Uma regra cria o checklist **uma vez por tarefa**: disparar de novo não duplica.

### Correções

- **A alteração de valor de propriedade personalizada** passou a entrar no
  mesmo funil de histórico das demais mudanças, com chave estável. Renomear a
  propriedade não quebra mais nada que dependa dela.

### Qualidade

- **`pnpm lint:api`**: o linter da API não tinha entrada local, e uma bateria
  "verde" cobria só metade do repositório.
- **Regra de lint desligada** cuja correção automática não compila neste alvo de
  TypeScript — ela editava código no gancho de pré-commit e quebrava o build.

## [1.17.1] — 2026-08-16

**Patch, e não minor**: nada de novo chega a quem usa o produto em produção. O
que entrou foram duas correções visíveis, uma trava de compilação e trabalho de
qualidade interno — a única funcionalidade do lote só existe no ambiente de
desenvolvimento, e fica inerte sem a variável que a liga.

### Correções

- **Duas etiquetas apareciam como identificador na tela.** No filtro por
  intervalo de datas, lia-se `common.date_range.after` no lugar de "Depois de".
  As chaves não existiam em nenhum idioma, e nada acusava isso: não quebra, não
  falha em teste e não erra na compilação. Achadas pela verificação nova.
- **Remover uma opção do meio da lista embaralhava o que estava sendo
  digitado.** Ao configurar uma propriedade de seleção, o campo reaproveitado
  fazia o texto pular de linha.

### Qualidade

- **Formato de filtro sem componente agora quebra o build.** Antes, quem
  acrescentasse um formato e esquecesse a tela teria um filtro que aparece, não
  aceita valor e não avisa ninguém.
- **Verificação de chave de tradução inexistente**, na CI. A que já existia
  compara os idiomas entre si e não pega a chave que não existe em lugar nenhum.
- **Os arquivos deste fork estão sem avisos de lint**, incluindo dois de
  acessibilidade. E o gancho de pré-commit voltou a ser usável: erro barra,
  aviso não — antes ele barrava por sujeira herdada, e o efeito prático era ser
  contornado sempre.

### Desenvolvimento

- **O login deixa de jogar todo mundo para um endereço só.** Com a chave
  ligada, o redirecionamento segue a origem de quem chamou, desde que ela já
  esteja na lista de origens permitidas. Ausente em produção.

## [1.17.0] — 2026-08-16

### Os seis tipos filtram pela tela

Texto, número e moeda entram no seletor de filtro, fechando a última lacuna do
recurso: agora **todos os seis tipos** de propriedade filtram pela interface.

| Tipo                     | Como filtra                                              |
| ------------------------ | -------------------------------------------------------- |
| Seleção única e múltipla | escolhendo opções, com as cores                          |
| Data                     | "é" um dia, ou "entre" dois                              |
| Texto                    | **contém** um trecho                                     |
| Número e moeda           | "é" um valor, ou "entre" dois — a moeda mostra o símbolo |

O que faltava era um formato de campo: os quatro que existiam são de
**escolher** (calendário ou lista), e esses três precisam de **digitar**.

Os campos confirmam ao sair — Enter confirma, Escape devolve o que estava —, e a
faixa só filtra com as duas pontas preenchidas: meia faixa mostraria um recorte
que ninguém pediu.

## [1.16.0] — 2026-08-16

### Filtrar por propriedade de data

A propriedade de **data** entra no seletor de filtro, com calendário e os
operadores **é** e **entre** — reaproveitando o mesmo componente que já atende
"Data de início" e "Data de conclusão".

O backend passou a aceitar o vocabulário da tela (`__exact` e `__range`) e o
traduz para o par `gte`/`lte` que já existia, em vez de manter dois formatos de
faixa. Faixa malformada continua sendo ignorada, e não vira consulta errada.

**Texto, número e moeda seguem só na API.** Eles precisam de um campo de
digitar, e o pacote de filtros ricos só oferece formatos de escolher; o motivo
técnico está medido no backlog.

### Correções

- **O seletor de filtros não abria no ambiente de desenvolvimento.** A instância
  de filtro era criada num `useMemo` e apagada no encerramento do efeito — sob
  `StrictMode`, que monta, desmonta e remonta o mesmo componente, sobrava uma
  referência órfã. Não afetava produção, mas obrigava a desligar o `StrictMode`
  para validar qualquer coisa que dependesse de filtros.

### Desenvolvimento

- **A limpeza passou a morar dentro do comando que faz a sujeira.** `pnpm
test:api` roda os testes e desliga a stack de teste ao terminar — ela ficava
  de pé consumindo quase dois núcleos de CPU sem atender ninguém. O deploy poda
  as imagens que o próprio build deixou órfãs.

## [1.15.0] — 2026-08-15

### O ícone da propriedade personalizada

Todo campo aparecia com o mesmo desenho de etiqueta — e ícone repetido não
informa nada, obriga a ler o nome de cada um.

- **Padrão por tipo**: texto é a letra, número o cerquilha, data o calendário,
  seleção a lista, múltipla as camadas, moeda o cifrão. Dois campos de tipos
  diferentes não nascem mais iguais.
- **Escolha explícita**, numa grade de 30 ícones na configuração da
  propriedade, com um caminho de volta ao padrão.
- O ícone aparece na configuração, no painel da tarefa, no cabeçalho da coluna
  da tabela e no seletor de filtro.
- A API pública e o webhook devolvem o ícone **efetivo**, já resolvido.

### Desenvolvimento

- **O servidor de desenvolvimento abre por outro nome de host.** O Vite 6
  confere o cabeçalho `Host` contra DNS rebinding e só aceitava `localhost` e
  IPs — pelo nome do tailnet devolvia 403 da própria aplicação, disfarçado de
  problema de rede. Junto, a API passou a ser servida pela mesma origem da
  página, como em produção: `localhost`, IP da rede e nome do tailnet funcionam
  ao mesmo tempo, sem CORS no caminho. Não afeta produção.

## [1.14.0] — 2026-08-15

### Os campos no webhook e na API pública

A tarefa já saía com os valores das propriedades, mas ali um campo é um id:
`{"e418d9f0-…": "88590486-…"}` não diz a ninguém que aquilo é "Canal =
Indicação". Agora diz.

- **Webhook**: a carga leva a **definição** dos campos que aquela tarefa
  preenche — nome, tipo, e o rótulo e a cor de cada opção. O receptor entende o
  que chegou sem precisar de uma segunda chamada, que é justamente o que um
  webhook nem sempre pode fazer. Só os campos preenchidos entram.
- **API pública**: as definições do projeto ganharam endereço próprio,
  `GET /api/v1/workspaces/<slug>/projects/<id>/issue-properties/`, na mesma
  ordem da tela. Definição muda pouco: lê-se uma vez e guarda.
- Os dois são só leitura. Criar campo é configuração do projeto, e continua
  tendo um caminho só.

### Correções

- **Valor de campo excluído continuava saindo.** A cascata que apaga os valores
  roda em tarefa assíncrona, e entre o clique e a tarefa — ou para sempre, se
  ela falhar — o valor seguia aparecendo na API e no webhook com o id de um
  campo que não existe mais. Encontrado ao conferir uma carga real de webhook,
  não por teste.

### Propriedades personalizadas nos menus da tela

As duas lacunas declaradas no lançamento — agrupar e filtrar por uma propriedade
**pela interface** — estão fechadas.

- **Agrupar por**: as propriedades de seleção única aparecem no menu junto com
  estado e prioridade. O quadro ganha uma coluna por opção, na ordem
  configurada, e "Nenhum" no fim.
- **Filtrar**: as propriedades de seleção, única ou múltipla, aparecem no
  seletor de filtro com as cores das opções. A condição sobrevive ao recarregar
  a página e a salvar a visão.
- A condição de propriedade passou a nascer como **subconsulta**, e não como
  junção: é o que permite duas propriedades na mesma expressão `and` sem que
  uma anule a outra — e faz o valor apagado parar de contar, o que a junção
  não fazia.
- A defesa contra nome de campo forjado continua inteira: um id de propriedade
  não entra na allowlist, mas passa pela mesma prova por outro caminho — UUID
  válido e propriedade existente antes de qualquer coisa tocar o ORM.

Texto, número, moeda e data continuam filtrando pela API e ainda não aparecem
no seletor visual.

## [1.13.1] — 2026-08-15

### Correções

- **Escrita recusada destruía o valor guardado.** O caminho de escrita apagava
  o valor antigo **antes** de validar o novo, e é a validação que recusa — então
  digitar casas decimais demais esvaziava o campo, e a pessoa perdia o número
  novo e o antigo ao mesmo tempo. O mais grave dos três, e o único que nenhum
  teste tinha pego.
- **A moeda ignorava as casas configuradas ao exibir.** A coluna do banco guarda
  seis casas, e o valor saía cru: um campo de duas casas mostrava `100,000000`.
  A correção anterior tinha tratado só a gravação.
- **Recusar deixava o campo vazio** em vez de devolver o último valor salvo.

## [1.13.0] — 2026-08-15

### Propriedades personalizadas

Campos próprios do processo de cada projeto, guardados na tarefa: valor de
contrato, data de aceite, canal de origem. Diferente de escrever na descrição,
eles filtram, ordenam, aparecem na tabela e saem na exportação.

- **Seis tipos**: texto, número, data, seleção única, seleção múltipla e moeda.
  Moeda declara a moeda e as casas decimais **na configuração**, não na tarefa —
  assim a coluna soma com sentido.
- **Configuração em Estrutura de tarefas**, ao lado de etapas, etiquetas e
  estimativas, com teto de 30 por projeto. Criar é porta de admin; preencher é
  de quem edita a tarefa.
- **Obrigatória impede criar, e só isso.** Não impede concluir e não alcança
  tarefas que já existiam: travar quem terminou o trabalho ensina a preencher
  qualquer coisa, e exigir o campo do passado viraria dívida do projeto inteiro.
- **Aparecem** no painel, no peek, na criação, no cartão (só as marcadas), na
  coluna da tabela, na exportação CSV e XLSX, na API pública e no webhook.
- **Cada mudança entra no histórico** da tarefa, com o nome do campo e o rótulo
  da opção — id não diz nada a quem lê meses depois.
- **Filtrar, ordenar e agrupar** funcionam pela API. Ordenação usa a coluna
  tipada — em texto, "10" viria antes de "9" — e seleção ordena pela ordem das
  opções, não pelo alfabeto.
- **A recorrência copia os valores** para cada ocorrência, na árvore inteira de
  subtarefas, sem elevar o custo por nó da cópia.
- **Trocar o tipo é proibido**, exceto seleção única → múltipla, que é a única
  conversão que não perde dado. Desativar preserva os valores.

- **A moeda exige as casas decimais configuradas.** Valor com mais precisão é
  recusado, com o número de casas na mensagem — arredondar dinheiro em silêncio
  trocaria o número digitado por outro, e a pessoa só descobriria no relatório.
- **Os campos de digitar salvam ao sair do campo**, não a cada tecla: Enter
  confirma, Escape desfaz. Salvar por tecla enchia o histórico da tarefa com
  uma linha por letra.

**Ainda não é possível escolher uma propriedade nos menus de "agrupar por" e
"filtrar por" da tela.** As duas coisas funcionam por trás, e quem integra pela
API já usa; o seletor visual depende de alargar uniões de tipo no pacote
compartilhado, o que atravessa toda a filtragem e as visões salvas.

### Infraestrutura

- **Cada compose do repositório ganhou nome de projeto próprio.** Nenhum
  declarava `name:`, então todos herdavam o nome do diretório — `plane`, o mesmo
  da produção. Foi assim que um `up` derrubou a API em 11/08, e o sintoma tinha
  voltado com os containers de teste aparecendo no `ps` da produção.

## [1.12.0] — 2026-08-14

### Tarefas recorrentes

- **Atalho no cabeçalho das tarefas**, ao lado do filtro, levando à auditoria
  das recorrentes do projeto. Ele só aparece quando **existe recorrência ativa**
  — atalho para tela vazia seria ruído permanente — e só para admin, que é quem
  a página atende. A auditoria já existia; o que faltava era alguém achá-la sem
  ir até Configurações → Execução.

## [1.11.0] — 2026-08-14

### Tarefas recorrentes

- **Pular uma ocorrência.** Cada uma das próximas datas, na seção "Repetir" da
  tarefa de origem, tem um botão **Pular** — só para admin do projeto. A data
  fica riscada e não vira tarefa; **Desfazer** no mesmo lugar a devolve. A
  semana do feriado deixa de exigir concluir uma tarefa que ninguém fez, ou
  desligar a recorrência e lembrar de religá-la.
- **Pular não mexe na série**: a ocorrência seguinte nasce no dia de sempre, e
  o contador de ocorrências criadas não sobe.
- **Não há confirmação, de propósito.** Nada foi criado, ninguém foi
  notificado, nenhum trabalho se perdeu — e modal para o que é barato ensina a
  confirmar sem ler, gastando a modal que importa.
- **Mudar a agenda descarta os pulos futuros**, com aviso **antes** de salvar e
  a contagem do que será descartado: a data pulada pode nem existir na agenda
  nova. Mudar só a antecedência não descarta nada, porque ela move o nascimento
  e não a data prevista.

## [1.10.0] — 2026-08-14

### Tarefas recorrentes

- **A ocorrência passa a copiar a árvore inteira de subtarefas**, em qualquer
  profundidade e com a hierarquia preservada — antes ia um nível só. A
  hierarquia descreve o trabalho, e a falta era invisível: o cartão da origem
  mostra a árvore toda, então ninguém percebia que a ocorrência nascia com o
  passo grande e sem os passos dele.
- **O teto de 50 subtarefas passou a contar a árvore**, e não as filhas
  diretas. É o que mantém o custo da geração onde estava — o mesmo número de
  tarefas criadas por ocorrência, distribuídas de outro jeito. Uma origem com
  50 filhas diretas continua copiando exatamente o que copiava.
- **O aviso de teto agora aparece** na seção "Repetir", quando a origem passa
  de 50. O corte na geração continua silencioso de propósito: a recorrência de
  ninguém é desativada por causa do limite.
- **O vencimento relativo da subtarefa vale em qualquer nível**, e não só no
  primeiro.

### Processo

- **A revisão do upstream ganhou o eixo dos avisos de segurança.** Só olhar
  release publicada deixava passar falha corrigida em silêncio: o Dependabot
  avisa quem consome pacote, e nós bifurcamos o código-fonte. Os **22 avisos**
  do Plane CE foram triados um a um contra o nosso código, e o histórico
  registra o veredito de cada um para que a revisão seguinte não recomece.
- **O sanitizador de HTML ganhou testes de ataque** — dez vetores clássicos de
  XSS contra `validate_html_content`, mais dois que provam que a formatação
  legítima e as tags do editor sobrevivem. A defesa já existia; o que faltava
  era alguém tentar quebrá-la sempre que a lista de permissão mudar.

## [1.9.0] — 2026-08-14

### Segurança

- **Convites de projeto passam a ser porta de admin.** `list`, `retrieve` e
  `destroy` herdavam apenas autenticação: qualquer pessoa do workspace lia ou
  apagava convites de qualquer projeto, inclusive de um do qual não participa —
  e o convite carrega o e-mail de quem foi convidado e o token bruto de aceite.
  Corresponde ao aviso `GHSA-r68c-48rr-m67f` do Plane CE, conferido no nosso
  código e corrigido antes de a release deles sair. Com teste de regressão.

### Tela da tarefa

- **Comentários vêm antes da atividade.** Eram um fluxo único, e o histórico
  automático — "mudou o estado", "definiu a prioridade" — afogava a conversa,
  que é a parte que alguém escreveu para ser lida.
- **As duas listas são recortadas**, com "Carregar mais": 5 comentários e 10
  linhas de atividade. O recorte guarda sempre os mais **recentes**, qualquer
  que seja a ordenação escolhida, e o botão fica acima deles — é de onde a
  conversa continua para trás.
- **A lista de subtarefas voltou a aparecer.** Ela se escondia sozinha: o
  marcador de visibilidade era um alternador, e o React executa cada efeito
  duas vezes em desenvolvimento — a segunda passada desfazia a primeira.

### Tarefas recorrentes

- **Vencimento relativo da subtarefa**: cada subtarefa da origem pode declarar
  "1 dia após o nascimento" ou "2 dias antes do vencimento" da ocorrência. Sem
  declaração, continua nascendo sem data. A data é calculada a cada ciclo, e
  nunca cai antes do dia em que a ocorrência nasce.
- **Responsável que sai do projeto**: a cópia o descarta, o painel marca a
  regra com conserto em um clique, e a remoção do membro avisa quantas
  recorrentes ficam afetadas e oferece transferir. A remoção nunca é travada, e
  a geração nunca para.
- **Responsável padrão do projeto** passa a valer nas ocorrências sem
  responsável — a regra valia em toda tarefa criada à mão e era ignorada
  justamente nas que nascem sozinhas.
- **Arquivar a origem agora avisa** que pausa a série, e o selo do quadro ganhou
  endpoint próprio, no lugar da listagem completa.

### Processo

- **Revisão de releases do upstream** vira processo documentado, com histórico
  que serve de ponto de partida da revisão seguinte. Só release publicada entra
  no escopo; aviso de segurança sem release vira exposição conhecida no log.
- **Matriz de compatibilidade** das tarefas recorrentes executada — 40 linhas
  com evidência, dois defeitos corrigidos e uma suspeita descartada.
- **Manual do usuário** das tarefas recorrentes: o comportamento observável, em
  linguagem de quem usa.

## [1.8.0] — 2026-08-13

### A recorrência mora na tarefa

Redesenho da funcionalidade entregue na 1.7.0, antes do primeiro uso amplo
(ADR 0010, revisão). O formulário paralelo de molde saiu: a regra passa a
apontar para uma **tarefa de origem**, que é o molde vivo — editar a tarefa
muda as próximas ocorrências, sem sincronizar nada.

- **Seção "Repetir" em todo cartão** (painel e peek): interruptor que só admin
  liga, com agenda, pausar e editar na própria tarefa. Subtarefa não tem
  recorrência própria; tarefa gerada mostra, no lugar do interruptor, o rastro
  **"Gerada pela recorrência de X"** — clicável, levando à origem.
- **Configurações viram painel de auditoria**: a página lista as tarefas com
  recorrência ativa (ID, próximas datas, abrir tarefa, pausar, excluir), sem
  botão de criar.
- **A ocorrência nasce na etapa inicial da regra** (padrão: a etapa padrão do
  projeto), nunca na etapa onde a anterior foi concluída — o defeito mais
  reclamado do Asana, onde a cópia nova aparece dentro da coluna Concluído e é
  reconcluída por engano.
- **Antecedência em dias e horas**: a tarefa nasce antes do vencimento ("3 dias
  antes", "2 horas antes"), com a data de nascimento virando data de início e o
  vencimento vindo da agenda. Horas valem até 23 — a partir de 24, usa-se dias.
- **O que a cópia carrega**: nome, descrição, prioridade, responsáveis,
  etiquetas, estimativa, tipo e subtarefas (um nível, abertas, **sem data** —
  data ausente não mente; a herdada do ciclo anterior nasceria vencida). Não
  carrega comentários, atividade, anexos, ciclo, módulo nem relações.
- **Ciclo de vida da origem**: concluir dispara a próxima no modo "após a
  conclusão"; arquivar pausa (reversível); excluir encerra a recorrência. As
  automações de arquivar e fechar **pulam origens ativas** — uma limpeza
  automática não pode pausar uma série em silêncio.
- **Guarda com critérios precisos**: a série inteira conta (origem e todas as
  ocorrências); cancelar e excluir liberam; concluir a anterior antes do
  vencimento resgata a ocorrência do período com a antecedência restante, e
  vencimento passado com a anterior aberta pula o período.
- **Selo "repete"** ao lado do ID nos layouts de lista e kanban.
- Migração converte cada molde existente numa tarefa de verdade, retomável por
  construção e ensaiada com dado real antes do deploy.

### Correções

- Ocorrência excluída ainda aberta não bloqueia mais a guarda — bloqueava a
  série para sempre, invisível no quadro.
- Modal aberto de dentro do peek não fecha mais o peek no primeiro clique
  (mesma correção da confirmação de conclusão, ADR 0009).

## [1.7.0] — 2026-08-13

### Tarefas recorrentes

Trabalho que se repete passa a ser configurado uma vez, em Configurações do
projeto → Execução → Tarefas recorrentes (ADR 0010). Só admin cria, porque a
regra gera trabalho para os outros.

- **Agenda flexível**: diária, semanal (vários dias numa regra só), mensal — por
  dia do mês, pelo último dia, ou pela 1ª/2ª/3ª/4ª/última ocorrência de um dia
  da semana — e anual, todas com intervalo, o que dá quinzenal nas duas leituras
  que a palavra tem. Fim por data, por contagem, ou nunca.
- **Dia que não existe no mês vira o último dia**: "todo dia 31" gera em 28/02 e
  30/04. A RFC 5545 mandaria pular esses meses, o que some com a tarefa cinco
  vezes por ano sem ninguém relacionar à causa.
- **Pré-visualização das próximas datas** no formulário, vinda do mesmo cálculo
  que vai gerar as tarefas — não de uma segunda implementação no front.
- **Duas formas de gerar**: por agenda, ou N dias após a conclusão da anterior.
- **Três guardas contra acúmulo**: atraso não gera as ocorrências perdidas, a
  ocorrência anterior aberta segura a próxima (opcional, ligada por padrão), e a
  mesma data nunca gera duas tarefas.

### Minhas tarefas

- Etapa cancelada ganha o mesmo fundo avermelhado que o estado cancelado tem no
  resto do produto.

## [1.6.1] — 2026-08-13

### Correções

- **Reabrir pelo campo de estado passa a seguir o estado escolhido.** A etapa
  pessoal ia sempre para a padrão, mesmo quando a pessoa escolhia
  "Em andamento". O botão de reabrir continua devolvendo a tarefa ao começo,
  porque ele manda a tarefa para o estado padrão do projeto; qualquer outro
  estado aberto é uma escolha, e a etapa segue o grupo dele.

## [1.6.0] — 2026-08-13

### Minhas tarefas acompanha o ciclo inteiro

A etapa pessoal só reagia à conclusão. Agora segue a mesma regra do projeto,
traduzida para etapas: entrar no grupo concluído leva à etapa de conclusão,
entrar no cancelado leva à de canceladas, e voltar para um grupo aberto devolve
à etapa padrão — como uma tarefa recém-atribuída. Andar entre grupos abertos
deixou de mexer em nada.

- **Reabrir devolve à etapa padrão.** A decisão original dizia que reabrir não
  desfazia o movimento, porque devolver à etapa anterior exigiria memória. O
  destino não é a anterior: é a padrão, sem memória nenhuma (revisão no ADR 0009).
- **Etapa "Canceladas" no seed**, sem a qual o cancelamento não teria onde
  aterrissar. Quem já tinha etapas recebe a nova por migração.
- **Marcação de qual etapa concluída é o destino** (`is_completion`), com a
  mesma apresentação do "Marcar como padrão" no painel de etapas.
- Correção: o "Marcar como conclusão" aparecia também no painel de etapas
  pessoais, onde não fazia nada.

### Cronograma em português

Datas, dias, meses, trimestres e duração deixaram de sair em inglês
("Aug 2026", "Week 32", "Th", "Q1", "9 days"). Os nomes passam a vir do locale
ativo, pelos mesmos ajudantes que o calendário já usava — some a segunda lista
de meses do código.

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
