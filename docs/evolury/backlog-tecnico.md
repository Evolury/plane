# Backlog técnico

Dívida que **atravessa funcionalidades** e por isso não cabe no backlog de
nenhuma delas. Cada item traz o número medido, não a impressão.

Backlogs de funcionalidade ficam em [funcionalidades/](funcionalidades/); este
arquivo é para o que sobra.

## Em aberto

### A coluna do quadro não acompanha o valor de propriedade mudado em outra aba

Com o quadro agrupado por propriedade personalizada (ADR 0011), mudar o valor em
outra aba atualiza a **pastilha** do cartão na hora — o aviso de tempo real
`propriedade` revalida a leitura de valores do projeto (ADR 0013) —, mas o
cartão **não muda de coluna** até recarregar.

O motivo é onde a informação mora: a coluna vem do campo `property_<uuid>` que o
servidor anota em cada tarefa da resposta agrupada, e o aviso de tempo real não
carrega esse campo. São duas leituras do mesmo dado, e o aviso atualiza só uma.

**Número medido:** 1 caso — quadro agrupado por propriedade, com mais de uma aba
aberta. Não afeta quem move o cartão (essa aba reagrupa sozinha, otimista).

**Caminho provável:** o receptor do aviso `propriedade` conferir se o
agrupamento atual é de propriedade e, se for, rebuscar a página; ou o aviso
passar a carregar propriedade e opção, e o receptor gravar o campo anotado no
store — que é o que `updateIssueList` já sabe reagrupar.

## Resolvido

### Migração nenhuma era executada por CI — 19/08/2026

O `pytest.ini` roda com `--nomigrations`: o banco de teste vem dos modelos, e as
migrações **nunca** eram executadas. Nenhum dos nove workflows subia banco ou
chamava `manage.py migrate`. **Vinte e quatro** migrações próprias entraram
assim — dependência errada, `RunPython` que quebra ou trava que conflita com
dado existente só apareceriam no deploy, em produção.

Apareceu de um jeito específico: uma injeção de defeito **dentro** de uma
migração não derrubou teste nenhum.

O workflow `Migrações` passou a subir Postgres e rodar dois passos:
`migrate --noinput` do zero, e `makemigrations --check --dry-run` para o inverso
— modelo alterado sem migração correspondente. Provado com defeito injetado, um
de cada vez: dependência apontando para migração inexistente e campo novo num
modelo derrubam a CI, cada um no seu passo.

### Diretório root do docker travava a troca de branch — 19/08/2026

`apps/api/plane/static-assets/collected-static` nasce do build da API,
pertence ao root e não estava em `.gitignore` nenhum. Vazio, não aparecia no
`git status` — mas o git tentava removê-lo ao trocar de branch, não conseguia, e
o `switch` falhava. Uma linha resolveu; conferido com o diretório presente, a
troca vai e volta.

### Rótulos do menu do editor - 19/08/2026

A contagem que eu tinha anotado ("38 literais") estava errada: os itens do editor
**já trazem** `i18n_name` ao lado do `name`, e o `name` é reserva. As 24 chaves
existiam e estavam traduzidas. O buraco era só nos pontos de render - a barra da
página lia o `name` direto. Corrigido, mais três literais de verdade ("Color",
"Full width", "Sticky toolbar").

### `no-use-before-define` - ligada em 19/08/2026

**A regra está ligada**, restrita a variáveis
(`{"functions": false, "classes": false, "variables": true}`) no `.oxlintrc.json`
— a forma que funciona; o `--rule-config` da linha de comando desliga a regra em
silêncio.

Das **180** ocorrências, **152 foram corrigidas de verdade**, em 53 arquivos, de
dois jeitos:

- **Arrow de escopo de módulo virou declaração de função.** Declaração é içada,
  então o uso antes da declaracao deixa de ser zona morta: o defeito some, não só
  o aviso. E o diff é de uma linha por símbolo, o que importa num fork que
  sincroniza com o upstream.
- **Declaração movida para antes do primeiro uso**, quando converter não cabia
  (componente em `observer`/`memo`, constante, genérico com anotação).

**As 28 restantes ficam congeladas pelo teto de avisos**, e é isso que impede a
volta do problema: uma ocorrência **nova** empurra a contagem acima do teto e
derruba a CI. Provado com defeito injetado.

Por que essas 28 não foram mexidas: são componentes referenciados no JSX de um
irmão (referência de renderização, nunca zona morta) e fechamentos locais cujo
uso está num `removeEventListener` de limpeza. Mover exigiria blocos grandes de
código herdado, e **três tentativas dessas eu tive de reverter**: o TypeScript
perde o estreitamento de tipo quando a função é içada para fora do `if` que a
protegia, e o movedor automático cortou errado em arquivos com genérico. O ganho
não paga o risco enquanto o teto segura a recorrência.

Quem reduzir esse número deve **baixar o teto junto**.

### Teto de avisos do lint que não segurava nada — 19/08/2026

O `apps/web` declarava `--max-warnings=11957` com **814 avisos reais**: cabiam
mais **11.143** antes de a CI reclamar. Os outros pacotes tinham folgas
parecidas (`apps/admin` 23/759, `apps/space` 56/676, `packages/propel` 59/3605).

É por isso que o aviso que denunciava o defeito da criação de página nunca
derrubou nada.

Todos os tetos passaram a ser o número real. Provado com defeito injetado: um
aviso novo em `apps/web` faz o `check:lint` sair com 1; removido, volta a 0.
Quem reduzir avisos deve **baixar o teto junto**, senão a folga volta.
