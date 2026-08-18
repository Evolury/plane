# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A varredura diária das etapas pessoais, no beat (ADR 0014)."""

from celery import shared_task

from plane.utils.etapas_por_vencimento import varrer_quem_virou_o_dia
from plane.utils.exception_logger import log_exception


@shared_task
def varrer_etapas_por_vencimento():
    """Roda de quinze em quinze minutos e atende quem acabou de virar o dia.

    A cadência não é desperdício: meia-noite é um instante POR FUSO, e um job
    diário atenderia bem só quem estivesse no fuso do servidor. Mesma solução e
    mesmo motivo das tarefas recorrentes (ADR 0010) e das automações agendadas
    (ADR 0012).
    """
    try:
        return varrer_quem_virou_o_dia()
    except Exception as erro:
        log_exception(erro)
        return 0
