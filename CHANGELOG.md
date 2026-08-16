# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento descrito em [VERSIONING.md](VERSIONING.md).

## [1.17.0] — 2026-08-16

### Os seis tipos filtram pela tela

Texto, número e moeda entram no seletor de filtro, fechando a última lacuna do
recurso: agora **todos os seis tipos** de propriedade filtram pela interface.

| Tipo | Como filtra |
| --- | --- |
| Seleção única e múltipla | escolhendo opções, com as cores |
| Data | "é" um dia, ou "entre" dois |
| Texto | **contém** um trecho |
| Número e moeda | "é" um valor, ou "entre" dois — a moeda mostra o símbolo |

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
