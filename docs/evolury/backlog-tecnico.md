# Backlog técnico

Dívida que **atravessa funcionalidades** e por isso não cabe no backlog de
nenhuma delas. Cada item traz o número medido, não a impressão.

Backlogs de funcionalidade ficam em [funcionalidades/](funcionalidades/); este
arquivo é para o que sobra.

## Em aberto

### 1. Rótulos do menu do editor ainda em inglês

**38 literais** — 17 em `packages/editor/src/core/components/menus/menu-items.ts`
e 21 em `packages/editor/src/core/constants/common.ts`: "Text", "Color", "Bold",
"Bulleted list", e assim por diante. Aparecem na barra de ferramentas de toda
página. Mais um: `Heading ${level}`, em
`packages/editor/src/core/extensions/placeholder.ts`.

Não é o mesmo problema do provedor de tradução, que já foi resolvido — estes são
**dados**, não JSX: viram `name: "Text"` dentro de listas de itens de menu.
Traduzir exige trocar o literal por chave e traduzir no ponto de renderização,
onde o `useEditorTranslation()` alcança.

Relacionado: [ADR 0004](decisoes/0004-idioma-unico-pt-br.md) (idioma único),
[ADR 0008](decisoes/0008-i18n-nos-pacotes-compartilhados.md) (como pacote
compartilhado traduz).

### 2. `no-use-before-define` continua desligada

**Medido em 19/08/2026:** 209 ocorrências com a regra crua; **181** com
`{"functions": false, "classes": false, "variables": true}` no `.oxlintrc.json`
— que é a forma que **funciona** (o `--rule-config` na linha de comando desliga
a regra em silêncio, sem avisar). As 181 são `const` recebendo função de seta e
usadas antes da declaração, espalhadas por ~60 arquivos, quase todos herdados do
upstream.

Foi exatamente essa classe de defeito que derrubou a criação de página por oito
dias (ver o `docs/evolury/funcionalidades/minhas-tarefas/backlog.md`, F8.4, e o
commit que a corrigiu).

**Por que não foi ligada:** reordenar declarações em ~60 arquivos do upstream
cria conflito em toda sincronização — ver [UPSTREAM.md](../../UPSTREAM.md). O
custo recorrente é maior do que o do defeito, **e o defeito já tem outra
guarda**: aquele caso emitia um aviso de `exhaustive-deps`, e o teto de avisos
apertado (abaixo) agora derruba a CI quando um aviso novo aparece.

Se um dia o fork divergir bastante do upstream a ponto de o conflito deixar de
importar, ligar é uma linha no `.oxlintrc.json` — e há prova de que a regra pega
o caso: reintroduzido o defeito, ela acusa os 6 usos.

## Resolvido

### Teto de avisos do lint que não segurava nada — 19/08/2026

O `apps/web` declarava `--max-warnings=11957` com **814 avisos reais**: cabiam
mais **11.143** antes de a CI reclamar. Os outros pacotes tinham folgas
parecidas (`apps/admin` 23/759, `apps/space` 56/676, `packages/propel` 59/3605).

É por isso que o aviso que denunciava o defeito da criação de página nunca
derrubou nada.

Todos os tetos passaram a ser o número real. Provado com defeito injetado: um
aviso novo em `apps/web` faz o `check:lint` sair com 1; removido, volta a 0.
Quem reduzir avisos deve **baixar o teto junto**, senão a folga volta.
