# Histórico de revisões do upstream

Log das revisões de release do Plane CE. Método em
[revisao-de-releases.md](revisao-de-releases.md).

**A revisão mais recente fica no topo.** Toda revisão nova começa lendo a
primeira entrada desta página, para saber de onde continuar.

---

## Estado atual

|                                     |                                 |
| ----------------------------------- | ------------------------------- |
| **Última release revisada**         | `v1.4.1` (upstream, 07/08/2026) |
| **Data da última revisão**          | 14/08/2026                      |
| **Releases pendentes**              | nenhuma                         |
| **Exposições conhecidas em aberto** | 1 — ver revisão de 14/08        |

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

**Situação:** em aberto. A correção do upstream existe em branch, sem release.
Decisão pendente do responsável pelo produto: esperar a release ou corrigir por
conta própria — são três decoradores.

### Achado de processo

A revisão foi feita olhando branches e commits, e o resultado mostrou por que
isso não escala: 19 branches em revisão, com títulos de limpeza cobrindo os
commits substantivos, e nenhuma garantia de que sobrevivem como estão. Daí a
regra de **só olhar release publicada** — e a exceção explícita para avisos de
segurança, que viram "exposição conhecida" em vez de trabalho imediato.

### Implementado

Nada. Não havia release nova a revisar.
