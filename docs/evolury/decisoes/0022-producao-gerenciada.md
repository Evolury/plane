# ADR 0022 — Produção na VPS: banco em casa por ora, arquivos no R2

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

**1. Computação, fila e banco na VPS; arquivos no R2.** O produto inteiro sobe
em contêiner num diretório só, com o Postgres junto. Arquivo é a única peça que
sai de casa desde o primeiro dia, porque disco de VPS é o pior lugar para
guardar upload de cliente: cresce sem aviso, não versiona, e some junto com a
máquina.

**2. O banco vai para o Neon quando houver 20 clientes, não antes.** A troca tem
um custo de aprendizado — pooler, cursor de servidor, dois endereços de conexão
— e um ganho que só aparece com volume: backup gerenciado, restauração pontual,
compute que acompanha a carga. Com dois clientes, esse ganho é teórico e o custo
é imediato.

Esperar **não** é adiar o preparo: o código já sabe funcionar atrás de um
agrupador de conexões, atrás de uma variável desligada. Ver "O que muda no
código".

**3. Backup do banco para o R2, no mesmo trilho da casa.** O bucket
`evolury-backups-locked` já guarda o acervo `restic` dos outros projetos da
casa. O QooWork entra nesse repositório com host e etiqueta próprios
(`--host qoowork --tag qoowork-db`), dump a cada 6 horas, guardando 8 últimos,
14 diários, 8 semanais e 6 mensais — dado de cliente pagante merece mais que
quatorze dias de memória.

Duas regras que o repositório compartilhado impõe: `forget` sempre escopado por
host e etiqueta, e **nunca `--prune` daqui** — prune tranca o repositório
inteiro e apaga dado de todos.

Um backup que nunca foi restaurado é esperança, não backup: a restauração foi
ensaiada em 22/08/2026, antes do primeiro cliente entrar, plantando uma marca na
produção e fazendo-a voltar do R2. O procedimento, o ensaio e a prova dos
guardas estão em
[backup e restauração](../processos/backup-e-restauracao.md).

**4. Arquivos no Cloudflare R2, em balde privado.** O produto já servia arquivo
por **URL assinada** — o `url()` do storage devolve a chave, e quem entrega é o
`generate_presigned_url`. Nada precisa ser público, e nada muda no caminho de
upload, que é presigned POST.

**5. A agenda das tarefas sai do banco e vai para um arquivo.** A agenda deste
produto vive em `beat_schedule`, versionada no código; o banco nunca foi a fonte
da verdade, era só a cópia. O `DatabaseScheduler` consulta o banco a cada poucos
segundos — irrelevante num Postgres nosso, caro num banco que cobra por estar
acordado.

**6. Imagens no GHCR, não construídas na produção.** Construir no servidor que
atende cliente é gastar oito minutos de CPU dele e depender de o repositório
estar lá. A casa já publica outros produtos em `ghcr.io/evolury/*`.

**7. E-mail pelo Brevo.** Deixa de ser pendência: sem entrega de e-mail ninguém
convida a equipe nem recupera acesso, e isso é bloqueio para cliente pagante.

**8. Instalação limpa.** A produção nova nasce vazia, com nome QooWork em tudo.
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

## Por que o Neon ficou para os 20 clientes

O motivo declarado para ir ao Neon era o _scale to zero_ — pagar só pelo que se
usa. Medido antes de decidir: **ele não aconteceria.** O compute suspende depois
de alguns minutos ocioso, e a agenda deste produto toca o banco a cada **5
minutos** (`stack_email_notification`) e a cada **15** (recorrentes, automações,
etapas por vencimento). Com uma consulta a cada cinco minutos, o relógio da
suspensão nunca chega ao fim.

Para dormir de verdade seria preciso espaçar essas rotinas — e o preço disso é
produto, não infraestrutura: notificação por e-mail chegando em até 15 minutos
em vez de 5, e automação marcada para as 08:00 podendo rodar às 08:30, o que
contradiz o que o [ADR 0012](0012-automacoes-personalizadas.md) promete.

Ou seja: a economia que justificava a mudança dependia de degradar o produto. Com
dois clientes, não vale. Com vinte, a conversa muda de figura — aí o que pesa é
backup gerenciado e restauração pontual, e não o compute ocioso.

**A cadência das tarefas fica como está.** Ela só mudaria para servir a uma
economia que não vamos ter agora.

## Alternativas descartadas

**Ir para o Neon agora.** Foi o plano por um dia, e caiu quando o _scale to
zero_ se mostrou inalcançável sem degradar o produto. O que sobrava — backup
gerenciado e restauração pontual — é comprável com `restic` e um ensaio de
restauração, por enquanto. Fica marcado para os 20 clientes.

**Manter os arquivos em MinIO na VPS.** Seria uma peça a menos para configurar
hoje. Mas upload de cliente em disco de VPS cresce sem aviso, não versiona e
morre com a máquina — e migrar arquivo depois é bem mais chato que migrar banco,
porque cada endereço já gravado no banco aponta para o lugar antigo.

**Trocar o RabbitMQ pelo Redis como fila.** Uma peça a menos. Trocar broker no
dia do lançamento é risco sem prazo para render — fica para quando houver
tempo de medir.

**Servir arquivo por balde público no R2.** Dispensaria URL assinada. Também
dispensaria o controle de quem vê o quê: anexo de tarefa privada viraria
endereço público adivinhável.

## Consequências

- O `BANCO_COM_POOLER` nasce **desligado** e sem uso: é preparo para a mudança
  dos 20 clientes, não código morto por descuido. Tem teste, e o teste é o que
  garante que ele ainda funcione quando for a hora.
- O arquivo da agenda precisa sobreviver a reinício, senão uma tarefa diária
  pode rodar duas vezes no mesmo dia — daí o volume no compose.
- `django_celery_beat` continua instalado e sem uso: as linhas que ele criou no
  banco deixam de ser lidas. Remover o aplicativo pediria migração própria, e
  não é urgente.
- A produção nova não tem MinIO, mas tem Postgres em contêiner — o
  `docker-compose` dela é diferente do desta máquina de qualquer forma (nomes
  QooWork, limites de recurso, sem porta exposta). São dois arquivos, e vão
  divergir; o daqui continua sendo o de desenvolvimento e validação.
- **O backup do banco passa a ser nosso problema**, e é o preço de manter o
  Postgres em casa. Dump a cada 6 horas para o R2, retenção diária, semanal e
  mensal, e um ensaio de restauração antes do primeiro cliente — feito em
  22/08/2026.
- **A definição da pilha passa a ser versionada** no repositório `infra`, em
  `qoowork/`. Backup de banco não é backup de sistema: com o dado no R2 e o
  `docker-compose.yml` só na VPS, perder a VPS seria ter o dado e não ter como
  servi-lo.
