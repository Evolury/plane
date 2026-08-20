# ADR 0008 — Pacotes compartilhados podem traduzir

- **Status:** Aceito (12/08/2026)
- **Relacionado:** [ADR 0004](0004-idioma-unico-pt-br.md) (idioma único)

## Contexto

No Plane, os pacotes do design system — `@plane/ui`, `@plane/propel` e
`@plane/editor` — são propositalmente livres de i18n: recebem texto por
propriedade e não sabem nada sobre idioma. Quem traduz é o app.

O problema é que nem todo texto desses pacotes chega por propriedade. Dois
ficavam presos em inglês na interface inteira:

- o campo de busca do `CustomSearchSelect` (`@plane/ui`), com o placeholder
  "Search" cravado — o componente aparece em **cerca de 50 telas**;
- a mensagem "Please enter a valid URL" do seletor de link do editor
  (`@plane/editor`).

As saídas possíveis eram passar o texto por propriedade em todos os pontos de
uso (~50 chamadas para um placeholder, e ainda deixaria o padrão em inglês
para quem esquecesse) ou deixar o pacote traduzir.

## Decisão

`@plane/ui`, `@plane/editor` e `@plane/propel` passam a depender de
`@plane/i18n` e traduzem os textos que nascem dentro deles, usando a função
`translate` (não o hook, para não impor contexto a componentes que podem
renderizar fora dele).

O que sustenta a escolha aqui e não no upstream: **este fork tem um idioma
só** (ADR 0004). A fronteira "pacote presentational sem i18n" existe para um
design system publicado, que precisa servir a qualquer app em qualquer idioma;
aqui os pacotes servem a um único produto, em pt-BR, e o custo de mantê-los
mudos é texto em inglês na cara do usuário.

Não há risco de ciclo de dependência: `@plane/i18n` depende apenas de
bibliotecas externas (i18next e React), de nenhum pacote interno.

## Extensão: constante carrega chave, nunca texto (20/08/2026)

A decisão acima trata do texto que nasce dentro de um pacote. A varredura de
20/08/2026 achou o mesmo defeito num lugar diferente e por um mecanismo
diferente — e ele era **maior**.

`packages/constants` declara **233** campos `i18n_*`. Em **46** deles o texto em
inglês vivia ao lado da chave, e num caso o comentário dizia por quê: "`name`
fica como rótulo cru de referência; a interface exibe `i18n_name`". A interface
não exibia. Metade dos consumidores lia o campo em inglês, e a tradução — que
existia, correta, nos dois locales — nunca chegava à tela.

**Constante passa a carregar a chave e só a chave.** Não é limpeza estética: com
os dois campos, escolher o errado compila e roda, e o defeito só aparece quando
alguém olha a tela; com um campo só, o compilador recusa. Foram **204** pontos
corrigidos, e cada consumidor foi apontado pelo `check:types`, não caçado à mão.

É a mesma lição do `contrastNote` registrada abaixo, aplicada a outro formato:
**o que é opcional não traduz nada sozinho.**

Dois corolários, ambos aprendidos na mesma varredura:

- **Identidade não se compara com rótulo.** `item.name === "Intake"` decidia a
  espessura de um ícone — traduzir o rótulo teria quebrado a tela sem erro
  nenhum. Identidade é `key`.
- **Nome de campo é contrato.** `IBaseLayoutConfig.label` guardava texto em
  inglês e o consumidor fazia `t(layout.label)`: passava o texto como se fosse
  chave, e o i18next devolvia o texto inalterado. O nome errado escondeu o
  defeito. Chave se chama `i18n_*`.

A verificação `literais-traduziveis` nasceu dessa varredura e é o que impede a
volta: ela falha quando um literal do código bate **letra por letra** com um
valor do `en`. Prova exata, não heurística — e por isso o workflow deixou de
filtrar por `packages/i18n/**`, senão nunca rodaria nos PRs que introduzem o
problema.

## Consequências

- Texto que nasce dentro de `ui`/`editor`/`propel` deve usar `translate` e ter
  chave nos dois locales, como em qualquer outro lugar do código.
- `@plane/propel` entrou depois, quando a varredura achou texto preso lá: o
  `aria-label` do botão de dispensar do `Banner`, o rótulo de leitor de tela do
  `Spinner` e o placeholder de busca do seletor de ícones. O `IconRoot` tinha
  ganhado antes uma prop `contrastNote` para receber o texto de fora, e nenhum
  chamador a passava — o inglês continuava na tela. É o mesmo desfecho que
  motivou a decisão: prop opcional em pacote presentational não traduz nada
  sozinha. A prop continua existindo para quem quiser sobrescrever; o padrão
  agora sai traduzido.
- Componentes desses pacotes continuam aceitando texto por propriedade quando
  o conteúdo é do domínio de quem chama — a tradução interna é para o texto
  que pertence ao próprio componente.
- **O servidor `live` passou a carregar i18n em runtime.** Ele depende de
  `@plane/editor`, que agora depende de `@plane/i18n` — então `i18next-icu`
  entra no grafo de um processo Node que roda em produção, e não só nos
  aplicativos de navegador, onde tudo é empacotado. Isso ficou visível quando a
  imagem de produção passou a instalar apenas as dependências reais de cada app
  (`pnpm deploy --prod`): `intl-messageformat` é **peer dependency** de
  `i18next-icu` e não estava declarada em lugar nenhum, sobrevivia por
  hoisting. O `live` subia e morria em `ERR_MODULE_NOT_FOUND`. A correção é
  declarar a peer explicitamente em `@plane/i18n`, que é quem de fato precisa
  dela em runtime. Ao mexer nas dependências desses pacotes, vale lembrar que
  agora existe um consumidor Node, não só navegador.
