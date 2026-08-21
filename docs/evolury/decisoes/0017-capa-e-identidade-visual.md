# ADR 0017 — A capa é cor; a imagem é escolha

- **Status:** Substituído por [ADR 0020](0020-qoowork-nome-e-identidade.md) (20/08/2026)
- **Relacionado:** [ADR 0004](0004-idioma-unico-pt-br.md) (idioma único), [ADR 0008](0008-i18n-nos-pacotes-compartilhados.md) (constante carrega chave, nunca texto)

## Contexto

Até a 1.31.0, todo projeto novo recebia uma **foto sorteada entre 29** e um
**emoji sorteado entre dezenas**; todo usuário sem foto recebia um círculo
verde-azulado `#028375` cravado no código, que não vem de lugar nenhum. Dois
projetos criados no mesmo minuto não tinham nada em comum, e a lista virava um
mosaico que ninguém escolheu.

O sorteio não é um defeito do upstream: é uma escolha de produto que faz sentido
para um SaaS multi-inquilino, onde a variedade disfarça o vazio inicial. Para um
produto com marca própria, ela troca identidade por ruído.

## A decisão

**1. Aparência de origem é a marca, e não um sorteio.** Capa vazia é pintada
pela tela com **NanoBlue `#0C91EB`**; o ícone de projeto novo é `view_kanban` em
**DeepBlue `#013F6E`**; avatar sem foto é NanoBlue. As cores vêm do brandbook
1.02 (p. 17) e moram em `packages/constants/src/marca.ts`.

**2. A capa pode ser uma cor.** O seletor de capa tem uma aba de cores — doze
tons, a marca primeiro —, ao lado de Imagens e Enviar. É a aba que abre: é a
escolha mais barata (não sobe arquivo, não depende de serviço de terceiro) e a
que combina com o padrão da casa.

**3. Cor tem campo próprio: `cover_color`.** Em `Project` e em `User`.

**4. Cor e imagem nunca coexistem.** Quem escolhe cor limpa a imagem, e
vice-versa — no mesmo payload. A precedência ainda existe num lugar só (`capaDe`)
porque dado antigo ou uma escrita por fora podem trazer as duas.

**5. A forma é exata e o servidor é quem cobra.** `#RRGGBB`, normalizado em
maiúsculas. O valor termina desenhado num `style` do navegador: "começa com #"
deixaria passar `#fff);background-image:url(…` e transformaria um campo de cor
em injeção de CSS. O front tem a mesma regra, e o front é sugestão.

**6. Pôr imagem ou trocar o ícone é ação de quem cria.** Nada é escolhido pelo
sistema além do ponto de partida.

## Por que campo próprio, e não `cover_image`

Foi medido, e não deduzido. `Project.cover_image` é `TextField` e aceitaria a
cor; `User.cover_image` é `URLField`, e a API respondeu:

```
PATCH /api/users/me/  {"cover_image": "#0C91EB"}
400  {"cover_image": ["Enter a valid URL."]}
```

As alternativas foram descartadas por escrito:

- **Afrouxar o `URLField` do usuário** resolveria a recusa e deixaria um valor
  que não é URL num campo que o resto do código lê como endereço de arquivo —
  `getFileURL` incluído. A ambiguidade cobra juros em toda tela nova.
- **`data:` URI com um SVG de um retângulo** seria uma URL válida e renderizaria
  em `<img>`. Guardaria um documento onde deveria haver sete caracteres, e o
  `URLValidator` do Django nem aceita o esquema `data:`.
- **Oferecer cor só onde o campo permite** (projeto sim, perfil não) seria um
  produto incoerente pela conveniência do banco.

## O que a medição mudou no desenho

Duas correções vieram de números, e não de gosto:

- **O véu escuro do cartão vale para qualquer capa.** Branco sobre NanoBlue dá
  **3,35:1** — abaixo dos 4,5:1 que o identificador de 11px exige. Com o véu, vai
  a 7,6:1. A versão anterior tirava o véu quando não havia foto.
- **A placa do ícone passou de `white/10` para `white/80`.** Com a capa já
  escurecida pelo véu, o ícone DeepBlue sobre `white/10` fica entre **1,1:1 e
  1,7:1** — some. Sobre `white/80` fica acima de **7:1** em todas as doze cores.

## Consequências

- **Custo de sincronia com o upstream**: dois campos aditivos e uma migração
  (`0150`). Aditivo é a forma mais barata de divergir — nada some, nada muda de
  tipo. Ver [UPSTREAM.md](../../../UPSTREAM.md).
- **A API v1 pública não expõe `cover_color`.** Um cliente da API que escreva
  capa continua escrevendo imagem, como antes. Se um dia integração precisar
  escolher cor, é um acréscimo pequeno — e uma decisão à parte.
- **Nada de dado existente muda.** Projeto com capa continua com ela.
- **Recados e etiquetas seguem sorteando cor**, de propósito: ali a variedade é a
  funcionalidade. O que este ADR ataca é a identidade inventada, não a cor com
  função.
- **Fica em aberto** a divergência entre o azul da marca (`#0C91EB`) e o token de
  marca do tema (`#006399`). Este ADR usa NanoBlue na identidade e não mexe no
  tema; alinhar os dois afeta botões, links e foco, e é decisão maior.
