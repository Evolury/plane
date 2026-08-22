# ADR 0022 — Produção gerenciada: banco no Neon, arquivos no R2, computação na VPS

- **Status:** Aceito (22/08/2026)
- **Relacionado:** [ADR 0020](0020-qoowork-nome-e-identidade.md) (QooWork), [ADR 0021](0021-faturamento-por-assinatura.md) (faturamento)

## Contexto

O QooWork vai ao ar em `qoowork.com.br` com clientes pagantes. Até aqui a única
instância era `plane.evolury.app.br`, nesta máquina, com **tudo** em contêiner:
Postgres, MinIO, RabbitMQ, Redis e os cinco serviços do produto. Serve para
desenvolver e para validar; não serve para cobrar de gente.

O que muda não é o produto — é onde o estado mora. E cada peça de estado que sai
de um contêiner nosso para um serviço gerenciado troca um problema por outro:
ganha durabilidade e perde controle sobre detalhes que só aparecem sob carga.

Medido no terreno antes de decidir:

| Onde                | O que há                                                                                                                                                                                                                |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VPS `evolury-cloud` | Ubuntu 24.04, 8 vCPU, 31 GB, 295 GB livres, Docker 29.5, 10 projetos e uma convenção escrita: Caddy na borda com origin cert da Cloudflare, `/docker/<projeto>`, redes `web` + `<projeto>-internal`, **nunca `ports:`** |
| `qoowork.com.br`    | Já nos nameservers da Cloudflare, ainda sem registro A                                                                                                                                                                  |
| Segredos            | `bws` já guarda Neon, Asaas de produção, R2 admin, token de DNS e a chave SMTP do Brevo                                                                                                                                 |

## A decisão

**1. Computação e fila na VPS; banco e arquivos, fora.** O que é repetível e
descartável fica em contêiner; o que é estado com valor sai para quem faz backup
melhor que nós.

**2. Postgres no Neon, com dois endereços.** O aplicativo fala pelo `-pooler`;
**migração, `pg_dump` e comando administrativo falam pelo endereço direto**. O
pooler é um PgBouncer em modo transação, e o modo transação não preserva estado
de sessão — a falha típica não se anuncia como _pooling_, aparece como
`prepared statement "s0" already exists` ou um `SET` que evapora na consulta
seguinte.

Duas coisas nos salvam de graça e vale saber por quê: o Django 5.2 com psycopg 3
já desliga _prepared statements_ por padrão (`prepare_threshold=None`), e o
produto não usa `CONN_MAX_AGE`, então não segura conexão entre requisições.

**3. Arquivos no Cloudflare R2, em balde privado.** O produto já servia arquivo
por **URL assinada** — o `url()` do storage devolve a chave, e quem entrega é o
`generate_presigned_url`. Nada precisa ser público, e nada muda no caminho de
upload, que é presigned POST.

**4. A agenda das tarefas sai do banco e vai para um arquivo.** A agenda deste
produto vive em `beat_schedule`, versionada no código; o banco nunca foi a fonte
da verdade, era só a cópia. O `DatabaseScheduler` consulta o banco a cada poucos
segundos — irrelevante num Postgres nosso, caro num banco que cobra por estar
acordado.

**5. Imagens no GHCR, não construídas na produção.** Construir no servidor que
atende cliente é gastar oito minutos de CPU dele e depender de o repositório
estar lá. A casa já publica outros produtos em `ghcr.io/evolury/*`.

**6. E-mail pelo Brevo.** Deixa de ser pendência: sem entrega de e-mail ninguém
convida a equipe nem recupera acesso, e isso é bloqueio para cliente pagante.

**7. Instalação limpa.** A produção nova nasce vazia, com nome QooWork em tudo.
Os espaços de teste continuam onde estão. Migrar dado de validação para dentro
de uma base que vai cobrar é herdar sujeira sem ganhar nada.

## O que muda no código

Três ajustes, e os três com a mesma característica: quebram **em produção, sob
carga**, e nunca no desenvolvimento.

| Ajuste                                                    | Sem ele                                                                                        |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `DISABLE_SERVER_SIDE_CURSORS` quando `BANCO_COM_POOLER=1` | `cursor "_django_curs_…" does not exist` no meio de uma exportação grande, sem padrão aparente |
| `AWS_DEFAULT_ACL = None`                                  | O R2 recusa `x-amz-acl` — não é opção ignorada, é erro                                         |
| `beat_schedule_filename` no lugar do `DatabaseScheduler`  | Consulta ao banco a cada poucos segundos, para sempre                                          |

A variável `BANCO_COM_POOLER` existe para que instância com Postgres próprio
continue usando cursor de servidor, que é melhor para varredura grande. O padrão
é o comportamento antigo.

## O que esta decisão **não** entrega

**Scale to zero, na prática, não vai acontecer** — e vale dizer isso antes de
alguém contar com a economia. Trocar o agendador tira a batida do próprio beat,
mas a agenda tem tarefas que tocam o banco a cada **5 minutos**
(`stack_email_notification`) e a cada **15** (recorrentes, automações). O Neon
suspende depois de alguns minutos ociosos; com uma tarefa a cada cinco, ele
praticamente não dorme.

Para dormir de verdade seria preciso espaçar essas rotinas — o que atrasa
notificação por e-mail e geração de tarefa recorrente na mesma medida. É decisão
de produto, não de infraestrutura, e fica para depois de haver uso real para
medir.

## Alternativas descartadas

**Manter o Postgres em contêiner na VPS.** Mais barato e mais rápido, e é o que
já fazemos. Perde o ponto: backup, PITR e restauração passariam a ser problema
nosso justamente quando o dado passa a ser de cliente pagante.

**Usar o endereço direto do Neon para tudo.** Simplifica — some a classe inteira
de problemas de pooling. Mas o número de conexões diretas é limitado pelo
tamanho do compute, e o produto sobe gunicorn com vários processos mais os
workers. O pooler existe para esse caso.

**Trocar o RabbitMQ pelo Redis como fila.** Uma peça a menos. Trocar broker no
dia do lançamento é risco sem prazo para render — fica para quando houver
tempo de medir.

**Servir arquivo por balde público no R2.** Dispensaria URL assinada. Também
dispensaria o controle de quem vê o quê: anexo de tarefa privada viraria
endereço público adivinhável.

## Consequências

- Duas URLs de banco no ambiente, e a diferença entre elas importa: usar a
  errada na migração falha de um jeito que não menciona pooling.
- O arquivo da agenda precisa sobreviver a reinício, senão uma tarefa diária
  pode rodar duas vezes no mesmo dia — daí o volume no compose.
- `django_celery_beat` continua instalado e sem uso: as linhas que ele criou no
  banco deixam de ser lidas. Remover o aplicativo pediria migração própria, e
  não é urgente.
- A produção nova não tem MinIO nem Postgres em contêiner — o `docker-compose`
  dela é menor que o desta máquina, e diferente. São dois arquivos, e vão
  divergir; o daqui continua sendo o de desenvolvimento e validação.
