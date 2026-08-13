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
