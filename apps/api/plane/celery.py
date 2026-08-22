# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os
import logging

# Third party imports
from celery import Celery
from pythonjsonlogger.json import JsonFormatter
from celery.signals import after_setup_logger, after_setup_task_logger
from celery.schedules import crontab

# Module imports
from plane.settings.redis import redis_instance

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.production")

ri = redis_instance()

app = Celery("plane")

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.beat_schedule = {
    # Intra day recurring jobs
    "check-every-five-minutes-to-send-email-notifications": {
        "task": "plane.bgtasks.email_notification_task.stack_email_notification",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    # A telemetria de instância não é agendada: esta instalação não envia métricas
    # para terceiros. Ver docs/telemetria.md para religar contra coletor próprio.
    #
    # Evolury: tarefas recorrentes (ADR 0010). De quinze em quinze minutos
    # porque a agenda tem horário — "toda segunda às 8h" com job diário seria
    # "toda segunda, em algum momento".
    "generate-recurring-work-items-every-fifteen-minutes": {
        "task": "plane.bgtasks.recurring_work_item_task.generate_recurring_work_items",
        "schedule": crontab(minute="*/15"),
    },
    # Evolury: automações agendadas (ADR 0012). Mesma cadência da recorrência,
    # e pelo mesmo motivo: a agenda tem horário, e "toda segunda às 8h" com um
    # job diário seria "toda segunda, em algum momento".
    "run-scheduled-automations-every-fifteen-minutes": {
        "task": "plane.bgtasks.automation_task.rodar_automacoes_agendadas",
        "schedule": crontab(minute="*/15"),
    },
    # Evolury: etapas pessoais pelo vencimento (ADR 0014). Mesma cadência das
    # duas acima, e pelo mesmo motivo — meia-noite é um instante por fuso, e um
    # job diário atenderia bem só quem estivesse no fuso do servidor.
    "sweep-work-stages-by-due-date-every-fifteen-minutes": {
        "task": "plane.bgtasks.etapas_por_vencimento_task.varrer_etapas_por_vencimento",
        "schedule": crontab(minute="*/15"),
    },
    # Occurs once every day
    "check-every-day-to-delete-hard-delete": {
        "task": "plane.bgtasks.deletion_task.hard_delete",
        "schedule": crontab(hour=0, minute=0),  # UTC 00:00
    },
    # Evolury: faturamento (ADR 0021). A conciliação roda depois da purga e
    # antes do resto — se um evento se perdeu, o conserto acontece de
    # madrugada, e não no dia em que o cliente reclama.
    # A régua roda antes da conciliação: primeiro o estado deriva do que já
    # sabemos, depois o Asaas corrige o que faltar. A ordem inversa faria a
    # conciliação trabalhar sobre um estado que a régua ainda ia mudar.
    "evolury-avancar-regua-de-faturamento": {
        "task": "plane.bgtasks.faturamento_regua.avancar_regua",
        "schedule": crontab(hour=1, minute=5),  # UTC 01:05
    },
    # Depois da régua e antes da conciliação: o excedente muda o valor, o fim
    # da promoção também, e a conciliação confere os dois contra o Asaas.
    "evolury-ajustar-excedentes": {
        "task": "plane.bgtasks.faturamento_excedente.ajustar_excedentes",
        "schedule": crontab(hour=1, minute=8),  # UTC 01:08
    },
    "evolury-encerrar-promocoes": {
        "task": "plane.bgtasks.faturamento_promocao.encerrar_promocoes",
        "schedule": crontab(hour=1, minute=10),  # UTC 01:10
    },
    "evolury-conciliar-assinaturas": {
        "task": "plane.bgtasks.faturamento_conciliacao.conciliar_assinaturas",
        "schedule": crontab(hour=1, minute=15),  # UTC 01:15
    },
    # De hora em hora porque fila interrompida é silenciosa: o Asaas para
    # depois de 15 falhas seguidas e ninguém avisa.
    "evolury-alarme-de-silencio-do-asaas": {
        "task": "plane.bgtasks.faturamento_conciliacao.alarme_de_silencio_do_asaas",
        "schedule": crontab(minute=20),
    },
    "check-every-day-to-archive-and-close": {
        "task": "plane.bgtasks.issue_automation_task.archive_and_close_old_issues",
        "schedule": crontab(hour=1, minute=0),  # UTC 01:00
    },
    "check-every-day-to-delete_exporter_history": {
        "task": "plane.bgtasks.exporter_expired_task.delete_old_s3_link",
        "schedule": crontab(hour=1, minute=30),  # UTC 01:30
    },
    "check-every-day-to-delete-file-asset": {
        "task": "plane.bgtasks.file_asset_task.delete_unuploaded_file_asset",
        "schedule": crontab(hour=2, minute=0),  # UTC 02:00
    },
    "check-every-day-to-delete-api-logs": {
        "task": "plane.bgtasks.cleanup_task.delete_api_logs",
        "schedule": crontab(hour=2, minute=30),  # UTC 02:30
    },
    "check-every-day-to-delete-email-notification-logs": {
        "task": "plane.bgtasks.cleanup_task.delete_email_notification_logs",
        "schedule": crontab(hour=2, minute=45),  # UTC 02:45
    },
    # Evolury: registro de execuções das automações (ADR 0012). Junto das
    # outras podas, e pelo mesmo motivo: o log é a resposta a "por que não
    # rodou?", e uma resposta que ninguém apaga vira uma tabela que só cresce.
    "check-every-day-to-delete-automation-runs": {
        "task": "plane.bgtasks.cleanup_task.delete_automation_runs",
        "schedule": crontab(hour=2, minute=50),
    },
    "check-every-day-to-delete-page-versions": {
        "task": "plane.bgtasks.cleanup_task.delete_page_versions",
        "schedule": crontab(hour=3, minute=0),  # UTC 03:00
    },
    "check-every-day-to-delete-issue-description-versions": {
        "task": "plane.bgtasks.cleanup_task.delete_issue_description_versions",
        "schedule": crontab(hour=3, minute=15),  # UTC 03:15
    },
    "check-every-day-to-delete-webhook-logs": {
        "task": "plane.bgtasks.cleanup_task.delete_webhook_logs",
        "schedule": crontab(hour=3, minute=30),  # UTC 03:30
    },
    "check-every-day-to-delete-exporter-history": {
        "task": "plane.bgtasks.exporter_expired_task.delete_old_s3_link",
        "schedule": crontab(hour=3, minute=45),  # UTC 03:45
    },
}


# Setup logging
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = JsonFormatter('"%(levelname)s %(asctime)s %(module)s %(name)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(fmt=formatter)
    logger.addHandler(handler)


@after_setup_task_logger.connect
def setup_task_loggers(logger, *args, **kwargs):
    formatter = JsonFormatter('"%(levelname)s %(asctime)s %(module)s %(name)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(fmt=formatter)
    logger.addHandler(handler)


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_scheduler = "django_celery_beat.schedulers.DatabaseScheduler"
