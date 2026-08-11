# Telemetria

**Esta instalação não envia dados para terceiros.** Nenhuma métrica sai da sua
infraestrutura por padrão, e não existe destino default configurado no código.

O Plane CE, do qual este produto deriva, enviava a cada 6 horas — e a cada start
de container da API — um pacote de métricas para `telemetry.plane.so`. Este
documento registra o que foi desligado, o que aquela coleta continha e como
religá-la contra um coletor próprio, se um dia for do interesse.

## O que foi desligado

| Onde                                                              | Mudança                                                                                                                                                               |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/api/plane/celery.py`                                        | A task `push-instance-metrics` não está mais no `beat_schedule` — não há coleta periódica                                                                             |
| `apps/api/plane/license/management/commands/register_instance.py` | Removido o `push_instance_metrics.delay()` que disparava um envio a cada start de container                                                                           |
| `apps/api/plane/license/management/commands/register_instance.py` | Removida a consulta a `api.github.com/repos/makeplane/plane/releases/latest`; a versão em execução vem de `APP_VERSION` (ou do `package.json`) e é a única referência |
| `apps/api/plane/license/models/instance.py`                       | `is_telemetry_enabled` passa a `default=False`; a migration `0007` desliga também as instâncias já registradas                                                        |
| `apps/api/plane/license/api/views/admin.py`                       | No setup, campo ausente no POST significa desligado                                                                                                                   |
| `apps/admin/components/instance/setup-form.tsx`                   | Checkbox de telemetria começa desmarcado (antes um `\|\| true` forçava marcado, ignorando o parâmetro de URL)                                                         |
| `apps/api/plane/utils/otlp_endpoints.py`                          | Sem endpoint default: sem `OTLP_ENDPOINT`, os helpers devolvem `None` e nada é exportado                                                                              |

O código da coleta (`apps/api/plane/license/bgtasks/telemetry_metrics.py`) e o
toggle no god-mode (Admin → General) foram mantidos de propósito: é o que permite
religar contra infraestrutura própria sem reimplementar nada.

## Instâncias que já rodaram a versão anterior

O beat usa `django_celery_beat.schedulers.DatabaseScheduler`: as entradas do
`beat_schedule` são gravadas no banco na primeira execução e **não** são apagadas
ao sair do código. Em qualquer instância que já tenha rodado uma versão anterior,
confira e remova o agendamento residual:

```bash
docker compose exec api python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
print(PeriodicTask.objects.filter(task__contains='telemetry_metrics').delete())
"
```

A migration `0007` cuida do outro lado (o flag `is_telemetry_enabled` das
instâncias existentes) automaticamente.

## O que a coleta contém, se religada

Nada de conteúdo: sem títulos de work item, descrições, comentários, e-mails,
nomes de usuário ou anexos. É volumetria, com identificação da instância.

**Por instância** — 9 gauges (`plane_instance_*_total`): `users`, `workspaces`,
`projects`, `issues`, `modules`, `cycles`, `cycle_issues`, `module_issues`,
`pages`. Atributos anexados a todos: `instance_id`, `instance_name`,
`current_version`, `latest_version`, `edition`, `domain` (derivado do `WEB_URL`),
`is_verified`, `is_setup_done`.

**Por workspace** — 6 gauges (`plane_workspace_*_total`): `projects`, `issues`,
`modules`, `cycles`, `members`, `pages`, para até 1000 workspaces
(`WORKSPACE_METRICS_LIMIT`), identificados por `workspace_id` e
**`workspace_slug`**.

O `workspace_slug` junto do `domain` é o ponto sensível: em uma instância que
hospeda clientes, esse par identifica quem são eles e quanto cada um cresce.
É a razão principal de a coleta estar desligada, e é o que precisa ser pesado
antes de apontá-la para qualquer destino que não seja da própria operação.

## Implementação futura: coletor próprio

Decisão registrada: **não vamos apontar para coletor próprio agora.** Os 15
gauges acima são contadores de negócio, obteníveis com um `SELECT count(*)` no
Postgres; não trazem nenhum sinal operacional (latência, erro, saúde de fila) que
justifique manter um coletor OTLP de pé só para isso.

Quando houver interesse real em observabilidade, o caminho é instrumentar
requisição/latência/erro na API — não reaproveitar estes contadores. O upstream
tem trabalho nessa direção na branch `feat/otel-api-observability`, que pode
servir de referência.

Se ainda assim for preciso religar a coleta atual, são três passos — todos
necessários, em qualquer ordem:

1. **Apontar o coletor.** `OTLP_ENDPOINT=https://otel.suaempresa.com` no
   ambiente da API e do worker. Opcionais: `OTLP_METRICS_PROTOCOL` (`grpc`
   default, ou `http`) e `OTEL_EXPORTER_OTLP_METRICS_INSECURE=true` para gRPC
   sem TLS em rede interna.

2. **Ligar na instância.** God-mode → Admin → General → toggle de telemetria.
   (Ou `Instance.objects.update(is_telemetry_enabled=True)`.)

3. **Reagendar a task**, em `apps/api/plane/celery.py`, dentro de
   `app.conf.beat_schedule`:

   ```python
   "push-instance-metrics": {
       "task": "plane.license.bgtasks.telemetry_metrics.push_instance_metrics",
       "schedule": schedule(run_every=timedelta(minutes=360)),
   },
   ```

   Requer reimportar `schedule` de `celery.schedules` e `timedelta` de
   `datetime`.

Faltando qualquer um dos três, a task retorna cedo sem exportar — e registra o
motivo em log `debug`.
