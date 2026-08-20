# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Os efeitos de uma exclusão em massa: histórico e aviso de tempo real.

Fora da requisição de propósito. Marcar as linhas é rápido — uma consulta por
relação — e o que demora é o resto: uma linha de histórico por tarefa e um aviso
por tarefa no Redis. Quem apertou o botão não precisa esperar por isso, e o
navegador já tirou os cartões da tela.

**Não notifica.** A exclusão de UMA tarefa avisa quem a acompanha, e isso faz
sentido: é um evento. Duzentas de uma vez são uma limpeza, e mandar duzentos
avisos para a mesma pessoa transformaria a caixa de entrada em lixo — o
histórico registra tudo, e é lá que se procura o que aconteceu (ADR 0018).
"""

from celery import shared_task

from plane.db.models import IssueActivity
from plane.utils.exception_logger import log_exception
from plane.utils.tempo_real import publicar_mudanca

#: O verbo que vai para o histórico e o evento que vai para o cliente.
#:
#: "criada" no desfazer não é folclore: o cliente que ouve "criada" REBUSCA a
#: lista, porque não sabe avaliar sozinho se a tarefa que voltou passa pelos
#: filtros de quem está olhando (ver `plane/utils/tempo_real.py`).
EFEITOS = {
    "deleted": ("deleted the issue", "issue.activity.deleted"),
    "restored": ("restored the issue", "issue.activity.created"),
}


@shared_task
def registrar_exclusao_em_massa(issue_ids, project_id, workspace_id, actor_id, epoch, verbo):
    efeito = EFEITOS.get(verbo)
    if efeito is None or not issue_ids:
        return

    comentario, tipo_do_evento = efeito

    try:
        IssueActivity.objects.bulk_create(
            [
                IssueActivity(
                    issue_id=issue_id,
                    project_id=project_id,
                    workspace_id=workspace_id,
                    comment=comentario,
                    verb=verbo,
                    field="issue",
                    actor_id=actor_id,
                    epoch=epoch,
                )
                for issue_id in issue_ids
            ],
            batch_size=100,
        )
    except Exception as erro:
        # Sem histórico a exclusão continua feita; levantar aqui só encheria a
        # fila de repetições que apagariam de novo o que já está apagado.
        log_exception(erro)

    for issue_id in issue_ids:
        publicar_mudanca(tipo_do_evento, issue_id, project_id, actor_id)
