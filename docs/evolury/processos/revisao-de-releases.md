# Revisão de releases do Plane CE

Instruções da revisão periódica do upstream. O histórico de cada execução fica
em [historico-de-revisoes.md](historico-de-revisoes.md), que é **o ponto de
partida obrigatório** de toda revisão nova.

## Por que este processo existe

O produto deixou de acompanhar o upstream em 11/08/2026 ([UPSTREAM.md](../../../UPSTREAM.md)),
e a contrapartida está escrita lá: **o Plane CE continua corrigindo falhas que
também existem no nosso código, e ninguém mais vai aplicá-las por nós.**

A revisão não é sincronização. Não rebaseamos, não adotamos a numeração deles e
não importamos release inteira. Lemos o que mudou, decidimos item a item, e
implementamos o que faz sentido — com a mesma disciplina de qualquer entrega
nossa.

## O que se olha, e o que não se olha

**Só release publicada.** A unidade de revisão é a
[release do GitHub](https://github.com/makeplane/plane/releases): tag, notas e o
diff entre a última tag revisada e a nova.

**Não se olha commit solto, branch aberta nem PR em revisão.** Código não
publicado muda, é revertido e às vezes nem chega a existir; revisar isso gera
trabalho que se perde. A exceção que confirma a regra está registrada na
revisão inicial do histórico — e é justamente por ela que a regra existe.

> **Aviso de segurança sem release ainda.** Se um GHSA público apontar para o
> Plane CE e a correção ainda não estiver em release, **anote no histórico como
> exposição conhecida** e avalie o risco. Não é motivo para abrir exceção no
> processo, é motivo para decidir conscientemente se esperamos a release ou se
> tratamos por conta própria.

## O passo a passo

### 1. Descobrir o ponto de partida

Abrir o [histórico](historico-de-revisoes.md) e ler a **última release
revisada**. Nunca começar de outro lugar — o histórico é o que garante que
nenhuma release passe despercebida entre uma consulta e outra.

### 2. Listar o que há de novo

```bash
git fetch upstream --tags
git tag --list 'v*' --sort=creatordate --merged upstream/master
```

Considerar apenas as tags **posteriores** à última revisada. Se não houver
nenhuma, a revisão termina aqui — e mesmo assim **registra-se a consulta no
histórico**, com o resultado "nenhuma release nova". Consulta sem achado é
informação: ela prova que a janela foi coberta.

### 3. Ler as notas de cada release

Uma release por vez, na ordem cronológica. As notas dizem a intenção; o diff diz
o que realmente mudou. Ler as duas, nessa ordem.

### 4. Levantar o diff no que nos alcança

```bash
git diff --stat <ultima-revisada>..<nova> -- apps/ packages/
```

Ignorar o que não roda aqui: `.github/`, documentação do upstream, testes de
recursos que não temos, edição paga.

### 5. Classificar cada mudança

| Classe             | O que é                                                         | Tratamento padrão                                                  |
| ------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Segurança**      | correção de falha, com ou sem GHSA                              | **Aplicar**, salvo prova de que não nos alcança                    |
| **Correção**       | defeito em código que rodamos                                   | Aplicar quando reproduzível aqui                                   |
| **Funcionalidade** | recurso novo                                                    | Decidir contra o nosso roadmap — nem tudo que eles fazem nos serve |
| **Dependência**    | bump de versão                                                  | Aplicar se for segurança; senão, avaliar                           |
| **Infra e build**  | docker, CI, scripts                                             | Avaliar; costuma conflitar com o nosso enxugamento                 |
| **Não aplicável**  | edição paga, recurso que não temos, arquivo que não existe aqui | Registrar o motivo e seguir                                        |

### 6. Conferir aplicabilidade de verdade

**Arquivo existir não é o mesmo que estar vulnerável.** Antes de portar, abrir o
nosso arquivo e confirmar que o padrão defeituoso está lá. Pode não estar por
dois motivos opostos, e os dois importam:

- já divergimos e o problema não existe aqui → registrar como "já coberto";
- divergimos e o problema existe **de outra forma** → a correção precisa de
  adaptação, não de cópia.

### 7. Implementar

Cada item aprovado segue o fluxo normal do repositório: branch, teste que
falha antes e passa depois, `pnpm check`, validação na stack isolada, PR com
CI verde. Correção de segurança **ganha teste de regressão** — sem ele, a falha
volta na próxima refatoração e ninguém percebe.

Um PR por assunto. Misturar cinco correções de segurança num PR só torna a
revisão impossível e o rollback caro.

### 8. Registrar no histórico

Toda revisão vira uma entrada, mesmo quando não encontrou nada. A entrada diz o
que foi olhado, o que foi decidido e **por quê** — inclusive o que foi
dispensado. Item dispensado sem motivo escrito volta a ser reavaliado do zero na
revisão seguinte, que é desperdício puro.

## Armadilhas conhecidas deste fork

**Numeração de migração colide.** O upstream estava na `0122` no corte; nós
estamos na `0139`, e todas as nossas de `0123` em diante são próprias. Se uma
release trouxer uma `0123` deles, o Django acusa duas folhas no grafo. A saída é
**renumerar a migração que chega** para depois da nossa última folha e ajustar
`dependencies` — nunca renumerar as nossas, que já rodaram em produção. O
aviso está escrito também em
[0123_evolury_default_language_pt_br.py](../../../apps/api/plane/db/migrations/0123_evolury_default_language_pt_br.py).

**Arquivo com comentário `Evolury:` é zona de conflito.** O comentário existe
para marcar exatamente isso. Ao portar algo que toque um desses arquivos,
consultar o ADR citado antes de aceitar a mudança de cima.

**As nossas decisões estruturais podem contradizer a mudança de lá.** Antes de
aplicar, conferir se o assunto esbarra em: idioma único pt-BR ([ADR 0004](../decisoes/0004-idioma-unico-pt-br.md)),
terminologia "tarefa" ([ADR 0003](../decisoes/0003-terminologia-tarefa-pt-br.md)),
semana no domingo ([ADR 0005](../decisoes/0005-semana-comeca-no-domingo.md)),
fuso ([ADR 0006](../decisoes/0006-fusos-do-brasil.md)), etapa pessoal
([ADR 0001](../decisoes/0001-minhas-tarefas-overlay-pessoal.md) e
[0002](../decisoes/0002-agrupamento-por-etapa-fonte-aditiva.md)), conclusão
([ADR 0009](../decisoes/0009-botao-concluir-tarefa.md)) e recorrência
([ADR 0010](../decisoes/0010-tarefas-recorrentes.md)).

**Funcionalidade que já construímos.** Se o upstream lançar algo que já temos —
recorrência, por exemplo —, a decisão padrão é **manter a nossa** e registrar a
comparação. Trocar implementação madura por outra só porque veio de cima
descarta as decisões que já validamos.

**i18n.** Chave nova do upstream chega em inglês. Passar pelo fluxo da skill
`translate`, nunca traduzir à mão no JSON.

## Com que frequência

Não há calendário fixo: a revisão é disparada por **release nova** ou por
pedido. Vale consultar quando uma entrega grande termina — é quando há espaço
para absorver mudança de fora sem atropelar trabalho em curso.
