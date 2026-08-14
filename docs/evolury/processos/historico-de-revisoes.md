# Histórico de revisões do upstream

Log das revisões do upstream. Método em
[revisao-do-upstream.md](revisao-do-upstream.md).

**A revisão mais recente fica no topo.** Toda revisão nova começa lendo a
primeira entrada desta página, para saber de onde continuar.

---

## Estado atual

|                                     |                                 |
| ----------------------------------- | ------------------------------- |
| **Última release revisada**         | `v1.4.1` (upstream, 07/08/2026) |
| **Data da última revisão**          | 14/08/2026                      |
| **Releases pendentes**              | nenhuma                         |
| **Exposições conhecidas em aberto** | nenhuma                         |
| **Avisos com veredito**             | 3 de 22                         |

---

## Registro de avisos de segurança

Um GHSA sai desta fila quando ganha veredito, e não volta. Sem este registro, a
revisão reverificaria os mesmos vinte avisos toda vez.

Nenhum dos 22 foi publicado depois do nosso corte (05/08/2026), o que **sugere**
que as correções vieram junto no código herdado — mas data é pista, não prova:
o veredito só vale conferido no nosso código.

| GHSA                  | Severidade | Publicado  | Veredito     | Evidência                                                                                             |
| --------------------- | ---------- | ---------- | ------------ | ----------------------------------------------------------------------------------------------------- |
| `GHSA-j77v-w36v-63v6` | crítico    | 2024-04-10 | **pendente** | —                                                                                                     |
| `GHSA-39gx-38xf-c348` | crítico    | 2024-10-11 | **pendente** | —                                                                                                     |
| `GHSA-cmwv-pjmw-8483` | crítico    | 2026-08-03 | coberto      | manifestos trazem placeholder explícito, e a produção usa chave própria do cofre                      |
| `GHSA-7j95-vh8g-f365` | crítico    | 2026-08-03 | **pendente** | —                                                                                                     |
| `GHSA-4vj8-p63v-8p24` | crítico    | 2026-08-03 | **pendente** | —                                                                                                     |
| `GHSA-mqjv-rwgv-4gxq` | crítico    | 2026-08-03 | **pendente** | —                                                                                                     |
| `GHSA-mq87-52pf-hm3h` | crítico    | 2026-08-03 | coberto      | `pinned_fetch` no webhook fixa o IP e não segue redirecionamento; o comentário no código cita o aviso |
| `GHSA-r2hw-fff3-pjwp` | crítico    | 2026-08-03 | **pendente** | —                                                                                                     |
| `GHSA-6fj7-xgpg-mj6f` | alto       | 2025-10-23 | **pendente** | —                                                                                                     |
| `GHSA-jcc6-f9v6-f7jw` | alto       | 2026-02-25 | **pendente** | —                                                                                                     |
| `GHSA-fpx8-73gf-7x73` | alto       | 2026-03-05 | **pendente** | —                                                                                                     |
| `GHSA-87x4-j8vh-p5qf` | alto       | 2026-03-05 | **pendente** | —                                                                                                     |
| `GHSA-9fr2-pprw-pp9j` | alto       | 2026-04-09 | **pendente** | —                                                                                                     |
| `GHSA-qw87-v5w3-6vxx` | alto       | 2026-05-15 | **pendente** | —                                                                                                     |
| `GHSA-rcg8-g69v-x23j` | médio      | 2025-01-06 | **pendente** | —                                                                                                     |
| `GHSA-rwjc-xhh3-m9m9` | médio      | 2025-08-14 | **pendente** | —                                                                                                     |
| `GHSA-7qx6-6739-c7qr` | médio      | 2026-01-02 | **pendente** | —                                                                                                     |
| `GHSA-rfj3-8c85-g46j` | médio      | 2026-02-23 | **pendente** | —                                                                                                     |
| `GHSA-4q54-h4x9-m329` | médio      | 2026-04-07 | **pendente** | —                                                                                                     |
| `GHSA-93x3-ghh7-72j3` | médio      | 2026-05-15 | **pendente** | —                                                                                                     |
| `GHSA-cjh4-q763-cc48` | baixo      | 2025-05-21 | **pendente** | —                                                                                                     |
| `GHSA-8rvg-7w43-p2w2` | baixo      | 2026-04-07 | **pendente** | —                                                                                                     |

Também existem **17 identificadores em rascunho**, vistos em branches abertas do
upstream e ainda não publicados. Não entram nesta tabela — ela é de avisos
públicos —, mas servem de pista: foi assim que a falha dos convites apareceu.

---

## 14/08/2026 — revisão inicial (base: `v1.4.1`)

Primeira execução, feita antes de o processo existir; foi ela que motivou o
processo. Cobre desde o ponto de corte do fork (`31853ab2b`, 05/08/2026).

### Releases novas

**Nenhuma.** A última release do upstream é a `v1.4.1`, de 07/08/2026 —
anterior ao nosso corte. Depois dela, a linha de desenvolvimento (`preview`)
recebeu **um único commit**, e o `master` não recebeu nenhum.

Em nove dias, o Plane CE não publicou funcionalidade nova.

### O que existe fora de release

Registrado aqui como contexto, **não como escopo de revisão** — é justamente o
tipo de material que o processo manda ignorar até virar release:

- 19 branches abertas de segurança, referenciando **17 avisos GHSA públicos**,
  nenhuma mesclada em `preview`;
- temas: IDOR e escopo por projeto, autorização faltando em rotas, visibilidade
  de convidado, SSRF no `live`, atribuição em massa e allowlists de ordenação;
- 32 dos 34 arquivos tocados existem no nosso fork. O ausente
  (`apps/live/src/lib/url-security.ts`) é **novo**, criado pela correção — ou
  seja, não temos essa proteção de forma alguma.

### Exposição conhecida, verificada

**Convites de projeto sem trava de admin** (`GHSA-r68c-48rr-m67f`).

Em [invite.py](../../../apps/api/plane/app/views/project/invite.py), o
`ProjectInvitationsViewset` tem `@allow_permission([ROLE.ADMIN])` apenas em
`create`. Os métodos `list`, `retrieve` e `destroy` herdam só
`IsAuthenticated` — qualquer pessoa do workspace lê ou apaga convites de outro
projeto, e o convite carrega **o e-mail do convidado e o token bruto**.

Conferido no nosso código, não inferido do upstream.

**Situação:** **corrigido em 14/08/2026**, por decisão de não esperar a release
do upstream. `list`, `retrieve` e `destroy` ganharam `@allow_permission([ROLE.ADMIN])`
em [invite.py](../../../apps/api/plane/app/views/project/invite.py), com teste de
regressão em `test_project_invitation_admin_scope.py` — quatro cenários que
falhavam antes e passam depois, incluindo o pior caso (alguém do workspace que
nem participa do projeto lendo os convites dele), mais um que prova que o admin
continua administrando.

Aproveitado no mesmo passo: o import `User` sem uso no arquivo, que o upstream
também remove na correção dele.

### Achado de processo

A revisão foi feita olhando branches e commits, e o resultado mostrou por que
isso não escala como fonte: 19 branches em revisão, com títulos de limpeza
cobrindo os commits substantivos, e nenhuma garantia de que sobrevivem como
estão. Daí a regra de **nunca portar código não publicado**.

**Revisado no mesmo dia, depois de conferir a página de avisos.** O processo
nascera olhando só releases, e isso deixava um buraco: o Plane tem 22 avisos de
segurança públicos, e nenhum alerta automático chega até nós — o Dependabot
avisa quem consome pacote, e nós bifurcamos o código-fonte. A revisão passou a
ter **dois eixos**, com o registro de avisos acima como memória do segundo.

Ficou também a distinção que faltava: um identificador GHSA é **pista legítima
venha de onde vier**, inclusive de branch aberta — o que não se adota é o código
deles; o que se investiga é a falha que o aviso nomeia, no nosso código.

### Implementado

Nada. Não havia release nova a revisar.
