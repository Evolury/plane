# Revisão do upstream (Plane CE)

Instruções da revisão periódica. O histórico de cada execução fica em
[historico-de-revisoes.md](historico-de-revisoes.md), que é **o ponto de partida
obrigatório** de toda revisão nova.

A revisão tem **dois eixos independentes**, e os dois são obrigatórios:

| Eixo                    | O que dispara       | Como se verifica                               |
| ----------------------- | ------------------- | ---------------------------------------------- |
| **Releases**            | tag nova publicada  | diff entre a última revisada e a nova          |
| **Avisos de segurança** | GHSA novo publicado | conferir no **nosso** código se a falha existe |

Eles são separados porque respondem a perguntas diferentes. A release pergunta
"o que mudou lá?"; o aviso pergunta "isto que eles corrigiram existe aqui?".
Um aviso pode sair sem release, e uma release pode sair sem aviso.

## Por que este processo existe

O produto deixou de acompanhar o upstream em 11/08/2026 ([UPSTREAM.md](../../../UPSTREAM.md)),
e a contrapartida está escrita lá: **o Plane CE continua corrigindo falhas que
também existem no nosso código, e ninguém mais vai aplicá-las por nós.**

A revisão não é sincronização. Não rebaseamos, não adotamos a numeração deles e
não importamos release inteira. Lemos o que mudou, decidimos item a item, e
implementamos o que faz sentido — com a mesma disciplina de qualquer entrega
nossa.

## O que se olha, e o que não se olha

**Nunca se porta código não publicado.** Branch aberta e PR em revisão mudam,
são revertidos e às vezes nem chegam a existir; adotar isso gera trabalho que se
perde.

**Mas um identificador GHSA é uma pista legítima, venha de onde vier** —
inclusive de uma mensagem de commit numa branch aberta. A distinção que importa:

> **Não adotamos o código deles; investigamos a falha que o aviso nomeia.**
> A pista é externa e instável; a evidência é o nosso código, que é estável e
> está aqui. Foi assim que a falha dos convites (`GHSA-r68c-48rr-m67f`) foi
> encontrada e corrigida em 14/08/2026, antes de o upstream publicar.

**Data de publicação é pista, não prova.** O fluxo normal é o aviso sair depois
da correção, então um aviso anterior ao nosso corte _provavelmente_ já está
coberto. "Provavelmente" não basta para segurança: **confere-se no código**. Foi
o que mostrou que o SSRF de webhook (`GHSA-mq87-52pf-hm3h`) está corrigido aqui
— o próprio comentário no código cita o aviso.

## O passo a passo

### 1. Descobrir o ponto de partida

Abrir o [histórico](historico-de-revisoes.md) e ler a **última release
revisada**. Nunca começar de outro lugar — o histórico é o que garante que
nenhuma release passe despercebida entre uma consulta e outra.

### 2a. Listar os avisos de segurança

```bash
# O `gh` não está instalado nesta máquina; o token vem do cofre.
TOKEN=$(bws secret get 2423fa31-822d-4555-be31-b46a002fdb63 \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["value"])')

curl -s -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/makeplane/plane/security-advisories?per_page=100" \
  > avisos.json

python3 -c '
import json
for a in json.load(open("avisos.json")):
    print(a["ghsa_id"], "|", a["severity"], "|", a["published_at"][:10], "|", a["summary"])
'
```

O JSON guarda também o campo `description`, que traz a análise técnica do
autor — é dele que sai o ponto exato a procurar no nosso código. Vale manter o
arquivo até o fim da revisão em vez de refazer a chamada a cada aviso.

Comparar com o **registro de avisos** no histórico e separar os que ainda não
têm veredito. Ordem de trabalho por severidade: `critical` e `high` são
verificados na hora; `medium` e `low` podem esperar a próxima revisão, desde que
o registro diga que estão pendentes.

Nenhum alerta automático chega até nós: o Dependabot avisa quem **consome um
pacote**, e nós bifurcamos o código-fonte. Esta consulta é o nosso único radar.

### 2b. Listar as releases novas

```bash
git fetch upstream --tags
git tag --list 'v*' --sort=creatordate --merged upstream/master
```

Considerar apenas as tags **posteriores** à última revisada. Se não houver
nenhuma, a revisão termina aqui — e mesmo assim **registra-se a consulta no
histórico**, com o resultado "nenhuma release nova". Consulta sem achado é
informação: ela prova que a janela foi coberta.

### 3. Dar veredito a cada aviso pendente

Para cada GHSA sem veredito, abrir a descrição, achar o ponto vulnerável e
**procurá-lo no nosso código**.

**Comece procurando o próprio identificador.** Boa parte das correções herdadas
cita o aviso no comentário, e isso resolve o veredito em segundos:

```bash
grep -rn "GHSA-xxxx-xxxx-xxxx" apps/ --include=*.py --include=*.ts*
```

**Depois, procure teste que já cubra.** `plane/tests/unit/bg_tasks/test_ssrf_advisories.py`
nomeia no cabeçalho todos os avisos de SSRF que cobre, e
`plane/tests/unit/utils/test_html_sanitization_xss.py` faz o mesmo para XSS
armazenado. Rodar a suíte vale mais que ler o código.

**Prove executando, não lendo.** Para veredito de segurança, leitura de código
convence e engana: foi atacando o sanitizador com `<script>`, `onerror` e
`javascript:` que o último aviso ganhou veredito — o código _parecia_ certo
antes disso, e a suposição inicial sobre onde a defesa morava estava errada.

**Confira todos os caminhos de escrita, não só o do app.** A API pública
(`plane/api/`) e a do app (`plane/app/`) têm serializers separados. Uma defesa
que exista só num dos dois é contornável por quem tem token externo — a
verificação do XSS só ficou honesta depois de conferir os dois.

Três resultados possíveis, todos registrados:

| Veredito              | Significa                                                               |
| --------------------- | ----------------------------------------------------------------------- |
| **coberto**           | a correção já está aqui — herdada no corte ou aplicada depois           |
| **corrigido por nós** | a falha existia e foi corrigida; com teste de regressão                 |
| **não aplicável**     | o código afetado não existe nesta edição, ou o caminho não é alcançável |

"Não aplicável" leva o motivo escrito. Sem ele, o aviso volta a ser
investigado do zero na revisão seguinte.

### 4. Ler as notas de cada release

Uma release por vez, na ordem cronológica. As notas dizem a intenção; o diff diz
o que realmente mudou. Ler as duas, nessa ordem.

### 5. Levantar o diff no que nos alcança

```bash
git diff --stat <ultima-revisada>..<nova> -- apps/ packages/
```

Ignorar o que não roda aqui: `.github/`, documentação do upstream, testes de
recursos que não temos, edição paga.

### 6. Classificar cada mudança

| Classe             | O que é                                                         | Tratamento padrão                                                  |
| ------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Segurança**      | correção de falha, com ou sem GHSA                              | **Aplicar**, salvo prova de que não nos alcança                    |
| **Correção**       | defeito em código que rodamos                                   | Aplicar quando reproduzível aqui                                   |
| **Funcionalidade** | recurso novo                                                    | Decidir contra o nosso roadmap — nem tudo que eles fazem nos serve |
| **Dependência**    | bump de versão                                                  | Aplicar se for segurança; senão, avaliar                           |
| **Infra e build**  | docker, CI, scripts                                             | Avaliar; costuma conflitar com o nosso enxugamento                 |
| **Não aplicável**  | edição paga, recurso que não temos, arquivo que não existe aqui | Registrar o motivo e seguir                                        |

### 7. Conferir aplicabilidade de verdade

**Arquivo existir não é o mesmo que estar vulnerável.** Antes de portar, abrir o
nosso arquivo e confirmar que o padrão defeituoso está lá. Pode não estar por
dois motivos opostos, e os dois importam:

- já divergimos e o problema não existe aqui → registrar como "já coberto";
- divergimos e o problema existe **de outra forma** → a correção precisa de
  adaptação, não de cópia.

### 8. Implementar

Cada item aprovado segue o fluxo normal do repositório: branch, teste que
falha antes e passa depois, `pnpm check`, validação na stack isolada, PR com
CI verde. Correção de segurança **ganha teste de regressão** — sem ele, a falha
volta na próxima refatoração e ninguém percebe.

Um PR por assunto. Misturar cinco correções de segurança num PR só torna a
revisão impossível e o rollback caro.

### 9. Registrar no histórico

Toda revisão vira uma entrada, mesmo quando não encontrou nada. A entrada diz o
que foi olhado, o que foi decidido e **por quê** — inclusive o que foi
dispensado. Item dispensado sem motivo escrito volta a ser reavaliado do zero na
revisão seguinte, que é desperdício puro.

O **registro de avisos** é atualizado no mesmo passo: cada GHSA com veredito sai
da fila de pendentes para sempre. É ele que impede a revisão de reverificar os
mesmos vinte avisos toda vez.

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
