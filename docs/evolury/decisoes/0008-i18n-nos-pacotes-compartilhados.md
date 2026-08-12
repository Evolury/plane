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

`@plane/ui` e `@plane/editor` passam a depender de `@plane/i18n` e traduzem os
textos que nascem dentro deles, usando a função `translate` (não o hook, para
não impor contexto a componentes que podem renderizar fora dele).

O que sustenta a escolha aqui e não no upstream: **este fork tem um idioma
só** (ADR 0004). A fronteira "pacote presentational sem i18n" existe para um
design system publicado, que precisa servir a qualquer app em qualquer idioma;
aqui os pacotes servem a um único produto, em pt-BR, e o custo de mantê-los
mudos é texto em inglês na cara do usuário.

Não há risco de ciclo de dependência: `@plane/i18n` depende apenas de
bibliotecas externas (i18next e React), de nenhum pacote interno.

## Consequências

- Texto que nasce dentro de `ui`/`editor` deve usar `translate` e ter chave
  nos dois locales, como em qualquer outro lugar do código.
- `@plane/propel` segue sem a dependência: não foi encontrado texto preso lá.
  Se aparecer, o caminho é o mesmo.
- Componentes desses pacotes continuam aceitando texto por propriedade quando
  o conteúdo é do domínio de quem chama — a tradução interna é para o texto
  que pertence ao próprio componente.
