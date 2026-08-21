# ADR 0020 — A plataforma se chama QooWork

- **Status:** Aceito (20/08/2026)
- **Substitui:** [ADR 0017](0017-capa-e-identidade-visual.md) (a capa é cor; a imagem é escolha)
- **Relacionado:** [ADR 0003](0003-terminologia-tarefa-pt-br.md) (terminologia), [ADR 0004](0004-idioma-unico-pt-br.md) (idioma único), [ADR 0008](0008-i18n-nos-pacotes-compartilhados.md) (constante carrega chave, nunca texto)

## Contexto

Até a 1.34 o produto se chamava **Evotask** e vestia o azul da **Evolury** —
NanoBlue `#0C91EB` na capa e no avatar, DeepBlue `#013F6E` no ícone (ADR 0017).
Eram duas marcas convivendo: a empresa e o produto, com o produto herdando a
paleta da empresa.

A plataforma passa a se chamar **QooWork**, com manual próprio, e vai ao ar sob
`qoowork.com.br`. A Evolury segue como a empresa que a constrói — os cabeçalhos
de copyright e os marcadores de autoria no código continuam dela, porque dizem
quem detém o direito, e não como o produto se apresenta.

## A decisão

**1. QooWork em tudo que o usuário vê.** Títulos e metadados, textos traduzidos,
assinatura dos e-mails, nome da instância registrada, manifesto, ícones e o
logotipo do rodapé da barra lateral.

**2. O logotipo é o wordmark, e é TEXTO.** O manual define um wordmark puro,
composto na própria família da marca, com tracking negativo que cresce com o
tamanho — 64px/−40, 32px/−30, 18px/−20, 12px/−5. No rodapé são os 18px da
prancha de aplicação no produto. Exportá-lo como SVG traçado congelaria o
desenho e obrigaria a manter dois arquivos, claro e escuro, sincronizados com
uma fonte que já está carregada na página.

**3. A marca de app é o Q recortado do wordmark**, num quadrado arredondado
(raio 19/84 do lado), preto com a letra em Cloud — favicon, PWA e ícone de
toque. Foi rasterizado a partir do próprio wordmark, nos quatro tamanhos.

**4. A família é Schibsted Grotesk**, que o manual indica como substituta do
território Söhne. Söhne é licenciada e exigiria contrato para uso em produto;
Schibsted Grotesk é aberta e entra pelo `@fontsource-variable`, como a Inter
que ela substitui.

**5. A regra da cor é de PROPORÇÃO, não de matiz**: _"preto e branco primeiro;
Iris depois. A cor de assinatura ocupa no máximo 3% da superfície — sinal de
ação e importância, nunca preenchimento."_

É o que muda o desenho em relação ao ADR 0017, e não só o valor hexadecimal:

| O quê              | ADR 0017 (Evolury)          | Agora (QooWork)                 |
| ------------------ | --------------------------- | ------------------------------- |
| Capa vazia         | NanoBlue `#0C91EB`          | **Qoo Black `#18181B`**         |
| Ícone do projeto   | DeepBlue `#013F6E`          | **Qoo Black**                   |
| Avatar sem foto    | NanoBlue, letra branca      | **Mist `#E4E4E7`, letra preta** |
| Cor de ação (tema) | `#006399`, um terceiro azul | **Qoo Iris `#625BF6`**          |
| Paleta de capas    | 12 tons livres              | **9 tons do manual**            |

A capa **não** é Iris porque capa é superfície grande — pintá-la com a cor de
assinatura é exatamente o preenchimento que o manual proíbe. O ícone **não** é
Iris por medição: na placa clara sobre a capa ele dá **2,98:1**, contra
**10,9:1** do preto, e abaixo de 3:1 um ícone deixa de ser legível para quem
enxerga pouco. O avatar **não** é Iris porque uma tela de equipe com trinta
pessoas seria trinta manchas da cor de assinatura.

O Iris entra onde a ação mora — botão primário, estado ativo, progresso, links
—, e isso não é decidido componente a componente: a rampa `--brand-*` do tema
foi **regerada em torno dele**, preservando a luminosidade de cada degrau e
trocando matiz e croma. Vinte e quatro degraus, claro e escuro, com o
`--brand-default` valendo exatamente `#625BF6`.

**6. As nove cores de capa saem todas do manual** — os cinco neutros, a
assinatura e as três de estado com croma controlado. Uma capa lilás-neon num
produto que se define por "preto e branco primeiro" é a primeira rachadura da
identidade.

## O que não muda

- **Copyright e marcadores de autoria continuam "Evolury".** Trocar o titular
  do direito autoral é ato jurídico, não decisão de marca; e os comentários
  `// Evolury:` marcam o que é nosso e não do upstream — a informação continua
  verdadeira.
- **Recados e etiquetas seguem sorteando cor**, como desde o ADR 0017: ali a
  variedade é a funcionalidade.

## Consequências

- **Uma guarda nova impede a volta do nome antigo**: um teste falha se
  "Evotask" reaparecer em tela, tradução, e-mail ou constante. Foram 328 textos
  traduzidos e 40 arquivos — o que sobra de um nome antigo não quebra nada, só
  faz o produto se apresentar com dois nomes.
- **O domínio muda para `qoowork.com.br`**, e isso vive fora deste repositório:
  DNS, certificado, Cloudflare e as variáveis do compose de produção. O código
  já aponta para lá; a infraestrutura precisa acompanhar antes do próximo
  deploy.
- **A fonte troca em todo o produto.** Schibsted Grotesk tem métricas próprias:
  a interface fica alguns por cento mais estreita, e telas com largura fixa
  merecem um olhar na primeira semana.
