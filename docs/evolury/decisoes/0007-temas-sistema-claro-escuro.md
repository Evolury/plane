# ADR 0007 — Só preferência do sistema, claro e escuro

- **Status:** Aceito (12/08/2026)
- **Relacionado:** [ADR 0004](0004-idioma-unico-pt-br.md),
  [ADR 0005](0005-semana-comeca-no-domingo.md),
  [ADR 0006](0006-fusos-do-brasil.md)

## Contexto

O seletor de tema do Plane oferecia seis opções: preferência do sistema,
claro, escuro, alto contraste claro, alto contraste escuro e um tema
personalizado com escolha de cores.

As três últimas custam mais do que entregam neste produto. Os dois temas de
alto contraste são uma variação que a base do fork não exercita, e o tema
personalizado arrasta uma máquina inteira atrás de si: um painel de seleção
de cores, utilitários que injetam variáveis de CSS em tempo de execução, um
efeito no `StoreWrapper` que aplica e limpa esse CSS a cada troca, e quatro
campos extras guardados no JSON do perfil.

## Decisão

Ficam **preferência do sistema, claro e escuro**. Saem as duas variantes de
alto contraste e o tema personalizado.

A remoção alcança as três camadas que sustentavam as opções:

- `THEMES` e `THEME_OPTIONS` em `@plane/constants` — é essa lista que alimenta
  tanto o seletor das preferências quanto o do Power-K;
- a lista de temas do `ThemeProvider` (next-themes) no `root`, que precisa
  concordar com a constante, senão um valor antigo seguiria sendo aplicado;
- o painel `CustomThemeSelector` e o efeito de CSS do `StoreWrapper`, que
  ficaram sem gatilho e foram removidos.

A migração `0132` normaliza quem já estava num tema removido: alto contraste
cai no tema simples de mesma luminosidade e o personalizado segue o
`darkPalette` que a própria pessoa havia escolhido, descartando as chaves de
cor. Sem ela, o valor ficaria no banco sem seletor que o mostrasse e a tela
cairia no padrão sem explicar por quê.

## Consequências

- Uma preferência mais curta e sem estados que a interface não sabe desenhar.
- Os utilitários `applyCustomTheme`/`clearCustomTheme` continuam em
  `@plane/utils`: fazem parte do módulo de tema do pacote e não custam nada
  parados. Voltar a oferecer o tema personalizado é reverter o commit.
- Acessibilidade: se em algum momento houver demanda por alto contraste, o
  caminho recomendado é tratá-lo no design system (tokens de contraste), não
  como mais um tema selecionável.
