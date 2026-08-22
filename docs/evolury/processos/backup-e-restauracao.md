# Backup e restauração da produção

> Ambiente: `qoowork.com.br`, VPS `evolury-cloud`, diretório `/docker/qoowork`.
> A pilha versionada fica no repositório `infra`, em `qoowork/`.
> Decisão de fundo: [ADR 0022](../decisoes/0022-producao-gerenciada.md) — o
> Postgres fica em casa até os 20 clientes.

## O que é protegido, e o que não é

| Dado               | Onde vive                         | Como é protegido                                       |
| ------------------ | --------------------------------- | ------------------------------------------------------ |
| Banco Postgres     | volume `qoowork_pgdata`           | `pg_dump` 4×/dia → restic → R2                         |
| Anexos e imagens   | Cloudflare R2 (`qoowork-uploads`) | é o armazenamento primário; não se copia para si mesmo |
| Definição da pilha | repositório `infra`, `qoowork/`   | git                                                    |
| Segredos           | Bitwarden Secrets Manager         | fora daqui, de propósito                               |
| Imagens Docker     | GHCR                              | reconstruíveis a partir de uma tag                     |

Fila e cache (`qoowork_mq`, `qoowork_redis`) não entram: são estado transitório.
Perder a fila custa reprocessar; perder o banco custa o negócio.

## Como funciona

Dois sidecars, separados de propósito, cada um com o seu marcador:

```
qoowork-db ──pg_dump──► volume qoowork_backups ──restic──► R2 evolury-backups-locked
             (6 em 6h)      .last-success-db      (6 em 6h)   .last-success-offsite
```

A separação existe para que **"o dump saiu" nunca passe por "o dado está a
salvo"**. Só o segundo marcador significa isso, e só ele responde pela saúde do
`qoowork-offsite`.

### Três escolhas que parecem detalhe e não são

**O dump não é comprimido.** Parece desperdício e é o contrário: o restic
deduplica em blocos e comprime com zstd. Um `.gz` muda inteiro a cada byte
alterado no banco — o restic não acha bloco repetido nenhum e cada snapshot
vira cópia integral. Sem compressão local, o repositório compartilhado rende
9,9× de compressão e deduplica entre snapshots.

**O `forget` anda escopado, e o `prune` não anda.** O repositório é
compartilhado com os outros projetos da casa (222 snapshots de 14 hosts em
22/08/2026). `forget` sem `--host`/`--tag` aplicaria a retenção do QooWork ao
acervo do vizinho. E `prune` tranca o repositório inteiro enquanto apaga —
num repositório com vários escritores em horários diferentes, é a operação que
derruba o backup alheio. Recolher espaço é decisão de quem cuida do
repositório, não deste serviço.

**Dump truncado é descartado, não arquivado.** O script confere a linha de
fecho do `pg_dump` antes de publicar o arquivo. Um truncado silencioso é pior
que backup nenhum: enche o acervo de restauração impossível e a ausência só
aparece no dia do desastre.

## Restaurar

O procedimento abaixo é o mesmo do ensaio — a diferença é o banco de destino.

```bash
ssh evolury-cloud
cd /docker/qoowork

# 1. Ver o que existe. Sem o host, o restic lista o acervo dos outros também.
sudo docker exec qoowork-offsite restic snapshots --host qoowork

# 2. Baixar do R2 (não do disco local — a ideia é provar o R2).
sudo docker exec qoowork-offsite restic restore latest --host qoowork \
  --target /backups/_restauracao

# 3. Carregar. ON_ERROR_STOP=1 é obrigatório: sem ele o psql segue depois de
#    erro e entrega um banco pela metade parecendo pronto.
SENHA=$(sudo grep -m1 '^POSTGRES_PASSWORD=' /docker/qoowork/.env | cut -d= -f2-)
ARQ=$(sudo docker exec qoowork-offsite sh -c 'ls -t /backups/_restauracao/backups/*.sql' | head -1)
sudo docker exec -e PGPASSWORD="$SENHA" qoowork-pgbackup \
  psql -h qoowork-db -U qoowork -d postgres -c 'CREATE DATABASE qoowork_novo'
sudo docker exec -e PGPASSWORD="$SENHA" qoowork-pgbackup \
  sh -c "psql -h qoowork-db -U qoowork -d qoowork_novo -v ON_ERROR_STOP=1 -f $ARQ"

# 4. Limpar o material restaurado — ele fica no volume que o restic copia.
sudo docker exec qoowork-offsite rm -rf /backups/_restauracao
```

Para virar a produção para o banco restaurado, renomeie os bancos e reinicie
api, worker e beat. Não edite `DATABASE_URL` para apontar ao banco de ensaio:
o nome do banco aparece em mais de um lugar do ambiente.

> O passo 4 não é higiene: sem ele, o diretório restaurado entra no snapshot
> seguinte e o backup passa a fazer backup do próprio backup. Aconteceu no
> primeiro ensaio (531 KiB → 1,55 MiB). O script hoje exclui `/backups/_*`,
> mas o lixo continua ocupando o volume.

## O ensaio, e por que ele existe

Backup que nunca foi restaurado é esperança, não backup. O ensaio de 22/08/2026,
antes do primeiro cliente entrar, mediu o caminho inteiro:

1. Uma marca foi plantada numa tabela da produção.
2. Um ciclo completo rodou: `pg_dump` → restic → R2.
3. O snapshot foi baixado **do R2**, carregado num banco novo, e a marca
   voltou idêntica.
4. Estrutura conferida contra a produção: 128 tabelas, 883 índices,
   196 migrações, 39 linhas de configuração da instância — iguais dos dois lados.
5. A marca e os bancos de ensaio foram removidos.

Repetir a cada trimestre, e sempre depois de mudar a versão do Postgres.

## Os guardas, e a prova de que não são decorativos

Os dois healthchecks medem **frescura de marcador**, não existência de processo:
um laço que morreu em silêncio continua "de pé" para o Docker. O critério é
`agora - epoch < 2×intervalo + 10 min`, e o nome do arquivo é específico — um
glob deixaria o marcador do vizinho mascarar a falha deste, porque os dois
sidecars dividem o volume.

Provados por injeção, um defeito de cada vez, em 22/08/2026:

| Defeito injetado                            | O que se esperava                        | O que aconteceu                                                                       |
| ------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------- |
| `.last-success-db` envelhecido em 100 000 s | `qoowork-pgbackup` fica `unhealthy`      | `unhealthy` em 195 s (3 tentativas × 65 s); `healthy` de volta em 65 s após restaurar |
| `.last-success-offsite` envelhecido         | `qoowork-offsite` fica `unhealthy`       | idem, 195 s                                                                           |
| `pg_dump` dublê entregando dump truncado    | arquivo descartado, marcador não escrito | descartado; volume vazio; marcador ausente                                            |
| controle: mesmo dublê, dump completo        | arquivo publicado, marcador escrito      | publicado; marcador com `epoch` do momento                                            |

O controle da última linha é o que separa "o guarda pegou a truncagem" de
"o script falha sempre".
