# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Três promessas que o produto fazia e não cumpria, sem avisar ninguém.

O fio comum é o mesmo dos defeitos que já apareceram aqui: **falha silenciosa
com cara de sucesso**. Nenhuma das três aparece na tela, e nenhuma quebra teste
nenhum — elas só acumulam.
"""

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from plane.bgtasks.cleanup_task import get_email_logs_queryset
from plane.db.models import EmailNotificationLog, Issue, Project, ProjectMember, State


@pytest.fixture
def antigo():
    """Um instante seguramente além da janela de retenção."""
    return timezone.now() - timedelta(days=settings.EMAIL_LOG_RETENTION_DAYS + 5)


@pytest.mark.contract
@pytest.mark.django_db
class TestAFilaDeEmailNaoCresceParaSempre:
    """A poda olhava só `sent_at`, e nulo não casa com `<=`.

    Numa instância sem SMTP — ou durante qualquer indisponibilidade do servidor
    de e-mail — nada esvaziava a tabela: a fila é escrita a cada notificação, e
    o que não saiu ficava para sempre. Medido em produção antes da correção: 49
    registros, 0 enviados, e o número só subia.
    """

    def _registro(self, create_user, sent_at, created_at):
        log = EmailNotificationLog.objects.create(
            receiver=create_user,
            triggered_by=create_user,
            entity_identifier=create_user.id,
            entity="issue",
            sent_at=sent_at,
        )
        # `created_at` é `auto_now_add`: só dá para envelhecer depois de criar.
        EmailNotificationLog.objects.filter(pk=log.pk).update(created_at=created_at)
        return log

    def test_registro_velho_que_nunca_saiu_e_podado(self, db, create_user, antigo):
        """O caso que a poda não alcançava."""
        log = self._registro(create_user, sent_at=None, created_at=antigo)

        assert log.id in set(get_email_logs_queryset())

    def test_registro_velho_que_saiu_continua_sendo_podado(self, db, create_user, antigo):
        """A regra que já existia não pode ter sido perdida na correção."""
        log = self._registro(create_user, sent_at=antigo, created_at=antigo)

        assert log.id in set(get_email_logs_queryset())

    def test_registro_recente_que_nao_saiu_e_preservado(self, db, create_user):
        """Sem isto, podar tudo passaria nos dois testes acima.

        Um aviso recém-enfileirado pode estar só esperando a vez: apagá-lo seria
        trocar um vazamento por perda de mensagem.
        """
        log = self._registro(create_user, sent_at=None, created_at=timezone.now())

        assert log.id not in set(get_email_logs_queryset())


@pytest.fixture
def projeto(db, workspace, create_user):
    p = Project.objects.create(name="Apelidos", identifier="APL", workspace=workspace)
    ProjectMember.objects.create(project=p, member=create_user, workspace=workspace, role=20)
    State.objects.create(name="A fazer", project=p, workspace=workspace, group="unstarted")
    return p


@pytest.fixture
def cliente(db, create_user):
    c = APIClient()
    c.force_authenticate(user=create_user)
    return c


@pytest.mark.contract
@pytest.mark.django_db
class TestApelidoConfundivelNaoPassaEmSilencio:
    """`PATCH {"assignees": [...]}` respondia 204 e não fazia nada.

    O campo escrevível é `assignee_ids`; `assignees` só existe como leitura. O
    DRF descarta chave desconhecida sem dizer nada, então a escrita "dava certo"
    e o responsável não mudava. Custou duas rodadas de depuração aqui dentro.
    """

    def _tarefa(self, projeto, workspace):
        estado = State.objects.get(project=projeto)
        return Issue.objects.create(
            name="t", project=projeto, workspace=workspace, state=estado, sequence_id=1
        )

    def url(self, workspace, projeto, tarefa):
        return f"/api/workspaces/{workspace.slug}/projects/{projeto.id}/issues/{tarefa.id}/"

    @pytest.mark.parametrize("apelido,certo", [("assignees", "assignee_ids"), ("labels", "label_ids")])
    def test_apelido_e_recusado_dizendo_o_nome_certo(
        self, cliente, workspace, projeto, create_user, apelido, certo
    ):
        tarefa = self._tarefa(projeto, workspace)

        resposta = cliente.patch(
            self.url(workspace, projeto, tarefa), {apelido: [str(create_user.id)]}, format="json"
        )

        assert resposta.status_code == 400, resposta.data
        # A mensagem tem de dizer o campo certo: recusar sem ensinar troca uma
        # falha silenciosa por uma barulhenta e igualmente inútil.
        assert certo in str(resposta.data)

    def test_o_campo_certo_continua_funcionando(self, cliente, workspace, projeto, create_user):
        """Sem isto, recusar tudo passaria no teste acima."""
        tarefa = self._tarefa(projeto, workspace)

        resposta = cliente.patch(
            self.url(workspace, projeto, tarefa), {"assignee_ids": [str(create_user.id)]}, format="json"
        )

        assert resposta.status_code in (200, 204), resposta.data
        assert list(tarefa.assignees.values_list("id", flat=True)) == [create_user.id]

    def test_campo_desconhecido_qualquer_continua_sendo_ignorado(self, cliente, workspace, projeto):
        """A recusa é sobre o par que se confunde, e não sobre campo extra.

        Recusar qualquer desconhecido quebraria todo cliente que mande campo a
        mais, e o alcance seria a API inteira.
        """
        tarefa = self._tarefa(projeto, workspace)

        resposta = cliente.patch(
            self.url(workspace, projeto, tarefa), {"campo_que_nao_existe": 1, "name": "novo"}, format="json"
        )

        assert resposta.status_code in (200, 204), resposta.data
        tarefa.refresh_from_db()
        assert tarefa.name == "novo"
