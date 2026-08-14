# Histórico de revisões do upstream

Log das revisões do upstream. Método em
[revisao-do-upstream.md](revisao-do-upstream.md).

**A âncora é a tabela `Estado atual`, logo abaixo** — é dela que toda revisão
nova parte. As entradas ficam em ordem decrescente e contam o que aconteceu em
cada uma; a tabela diz onde paramos.

Atualizar a tabela é a escrita mais importante de uma revisão: sem ela, a
seguinte começa do lugar errado e nada denuncia o erro.

---

## Estado atual

|                                     |                                 |
| ----------------------------------- | ------------------------------- |
| **Última release revisada**         | `v1.4.1` (upstream, 07/08/2026) |
| **Data da última revisão**          | 14/08/2026                      |
| **Releases pendentes**              | nenhuma                         |
| **Exposições conhecidas em aberto** | nenhuma                         |
| **Avisos com veredito**             | 22 de 22                        |

---

## Registro de avisos de segurança

Um GHSA sai desta fila quando ganha veredito, e não volta. Sem este registro, a
revisão reverificaria os mesmos vinte avisos toda vez.

Nenhum dos 22 foi publicado depois do nosso corte (05/08/2026), o que **sugere**
que as correções vieram junto no código herdado — mas data é pista, não prova.
A triagem de 14/08/2026 conferiu os 22 **no nosso código**, um a um: 20
cobertos e 1 não aplicável — o pendente foi fechado no mesmo dia.

| GHSA                  | Severidade | Publicado  | Veredito      | Evidência                                                                                           |
| --------------------- | ---------- | ---------- | ------------- | --------------------------------------------------------------------------------------------------- |
| `GHSA-j77v-w36v-63v6` | crítico    | 2024-04-10 | coberto       | `validate_url` + `pinned_fetch` · 21 testes passam                                                  |
| `GHSA-39gx-38xf-c348` | crítico    | 2024-10-11 | não aplicável | `/_next/image` não existe: o front migrou para Vite                                                 |
| `GHSA-cmwv-pjmw-8483` | crítico    | 2026-08-03 | coberto       | manifestos com placeholder; produção com chave própria                                              |
| `GHSA-7j95-vh8g-f365` | crítico    | 2026-08-03 | coberto       | Gitea e GitLab só aceitam e-mail verificado                                                         |
| `GHSA-4vj8-p63v-8p24` | crítico    | 2026-08-03 | coberto       | `join` exige sessão e e-mail igual ao convidado; o código cita o aviso                              |
| `GHSA-mqjv-rwgv-4gxq` | crítico    | 2026-08-03 | coberto       | contador de tentativas por token no código mágico                                                   |
| `GHSA-mq87-52pf-hm3h` | crítico    | 2026-08-03 | coberto       | `pinned_fetch` fixa o IP e não segue redirecionamento · suíte SSRF                                  |
| `GHSA-r2hw-fff3-pjwp` | crítico    | 2026-08-03 | coberto       | `ProjectBulkAssetEndpoint` escopado por autor e workspace                                           |
| `GHSA-6fj7-xgpg-mj6f` | alto       | 2025-10-23 | coberto       | `get_safe_redirect_url` valida o `next_path`                                                        |
| `GHSA-jcc6-f9v6-f7jw` | alto       | 2026-02-25 | coberto       | suíte SSRF cobre o favicon do 'Adicionar link'                                                      |
| `GHSA-fpx8-73gf-7x73` | alto       | 2026-03-05 | coberto       | `validate_url` no serializer do webhook · CGNAT, 6to4, multicast                                    |
| `GHSA-87x4-j8vh-p5qf` | alto       | 2026-03-05 | coberto       | membros exigem `WorkspaceEntityPermission`, não anônimo                                             |
| `GHSA-9fr2-pprw-pp9j` | alto       | 2026-04-09 | coberto       | `TestFaviconRedirect`, citando o aviso                                                              |
| `GHSA-qw87-v5w3-6vxx` | alto       | 2026-05-15 | coberto       | cópia de asset restrita ao workspace de destino                                                     |
| `GHSA-rcg8-g69v-x23j` | médio      | 2025-01-06 | coberto       | SVG em `SCRIPT_CAPABLE_MIME_TYPES`: servido como anexo                                              |
| `GHSA-rwjc-xhh3-m9m9` | médio      | 2025-08-14 | coberto       | `nh3.clean` com lista de permissão na escrita, no app e na API pública · teste de regressão próprio |
| `GHSA-7qx6-6739-c7qr` | médio      | 2026-01-02 | coberto       | convidado recebe `UserLiteSerializer`, sem e-mail                                                   |
| `GHSA-rfj3-8c85-g46j` | médio      | 2026-02-23 | coberto       | mesmo escopo por workspace nos assets                                                               |
| `GHSA-4q54-h4x9-m329` | médio      | 2026-04-07 | coberto       | `IssueBulkUpdateDateEndpoint` filtra pelo `project_id` da URL                                       |
| `GHSA-93x3-ghh7-72j3` | médio      | 2026-05-15 | coberto       | `segment` conferido contra `VALID_ANALYTICS_FIELDS`                                                 |
| `GHSA-cjh4-q763-cc48` | baixo      | 2025-05-21 | coberto       | `UserSerializer` exclui senha e fixa campos de sistema                                              |
| `GHSA-8rvg-7w43-p2w2` | baixo      | 2026-04-07 | coberto       | e-mail no corpo do POST, não em parâmetro de URL                                                    |

Também existem **17 identificadores em rascunho**, vistos em branches abertas do
upstream e ainda não publicados. Não entram nesta tabela — ela é de avisos
públicos —, mas servem de pista: foi assim que a falha dos convites apareceu.

---

## 14/08/2026 (fim do dia) — a âncora do histórico

Conferido se o histórico registra o suficiente para a próxima revisão começar de
onde esta parou. **Registrava, mas por acidente**: a tabela `Estado atual`
existia porque eu a criei, e nenhuma instrução mandava atualizá-la.

O modo de falha era silencioso e vinha exatamente de quem faz o trabalho direito:
escrever a entrada da revisão, contar o que achou, e esquecer a tabela. O
documento continuaria parecendo completo, e a revisão seguinte partiria do
lugar errado sem nada denunciar.

Agora o passo 1 aponta para a tabela como âncora — não para a primeira entrada,
não para a memória de ninguém —, o passo 9 exige as três escritas em ordem de
importância, e o histórico diz na abertura que atualizar a tabela é a escrita
mais importante da revisão.

---

## 14/08/2026 (fim do dia) — auditoria do próprio processo

Conferido se o processo escrito basta para alguém executá-lo sem improviso.
**Não bastava**, e as cinco lacunas eram todas coisa aprendida executando e não
devolvida ao papel:

1. O comando de consulta usava `gh`, que **não está instalado** nesta máquina —
   quem seguisse ao pé da letra travava no primeiro passo. Trocado pelo `curl`
   com o token do cofre, e **executado literalmente** para provar: devolve os 22.
2. Faltava a técnica mais rápida de todas: **procurar o identificador do aviso
   no nosso código**. Boa parte das correções herdadas cita o GHSA no
   comentário. Testada em quatro avisos, achou os quatro.
3. Faltavam os arquivos de teste que **nomeiam os avisos que cobrem** — rodar a
   suíte vale mais que ler o código.
4. Faltava a regra de **provar executando, não lendo**: foi atacando o
   sanitizador que o último aviso ganhou veredito, e a suposição inicial sobre
   onde a defesa morava estava errada.
5. Faltava conferir **todos os caminhos de escrita** — app e API pública têm
   serializers separados, e defesa que existe só num dos dois é contornável por
   token externo.

Processo que só funciona com quem o escreveu ao lado não é processo. A
verificação de hoje é o que transforma a experiência de uma execução em
instrução para a próxima.

---

## 14/08/2026 (tarde) — triagem dos 22 avisos

Executada logo depois de o eixo de segurança entrar no processo. Cada aviso foi
conferido **no nosso código**, não deduzido da data de publicação.

**Resultado: 21 cobertos, 1 não aplicável.** Nenhuma exposição nova.

A hipótese de que o corte posterior às publicações nos cobriria se confirmou —
mas só depois de conferida. Em vários casos a evidência é direta: o código traz
o identificador do aviso no comentário, e existe uma suíte de 21 testes de
regressão de SSRF que nomeia os avisos que cobre.

**Não aplicável (1):** `GHSA-39gx-38xf-c348`, SSRF pelo `/_next/image` — esse
endpoint não existe aqui, porque o front migrou de Next.js para Vite. É o tipo
de veredito que só se dá lendo o próprio código: pela versão, pareceria
aplicável.

**O último pendente, fechado no mesmo dia:** `GHSA-rwjc-xhh3-m9m9`, XSS
armazenado em `description_html`. A suposição estava errada — a defesa não está
na renderização, e sim **na escrita**: `nh3.clean` com lista de permissão roda
nos serializers do app **e** da API pública, antes de qualquer coisa chegar ao
banco. Conferir os dois caminhos importava, porque um token externo escrevendo
direto na API pularia uma defesa que só existisse no app.

Em vez de aceitar a leitura do código, ataquei o sanitizador com os vetores
clássicos: `<script>` some, `onerror`, `onload` e `onclick` são removidos,
`javascript:` perde o `href`, `<iframe>` e `<svg>` desaparecem. Virou teste
nosso (`test_html_sanitization_xss.py`), porque a lista de permissão é editada
sempre que o editor ganha um nó novo — e uma tag executável entrando ali
passaria despercebida sem alguém tentando explorá-la.

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
