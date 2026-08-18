# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A varredura diária das etapas pessoais (ADR 0014).

As afirmações que mais importam aqui são as de **ausência** — "não se move",
"não sai", "não carimba". São as que envelhecem pior sem teste: no dia em que
alguém trocar um filtro ou inverter um `if`, nada avisa, e a leitura antiga do
código continua parecendo correta.

Três delas se implementam ao contrário com facilidade, e o sintoma é silencioso:

* o opt-out é de SAÍDA, nunca de chegada;
* a varredura não carimba data;
* balde sem etapa marcada não move ninguém.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from plane.db.models import (
    Issue,
    IssueAssignee,
    Project,
    ProjectMember,
    State,
    WorkStage,
    WorkStageIssue,
)
from plane.utils.etapas_por_vencimento import balde_da_tarefa, varrer

HOJE = timezone.now().date()


@pytest.fixture
def projeto(db, workspace, create_user):
    p = Project.objects.create(name="Etapas", identifier="ETP", workspace=workspace)
    ProjectMember.objects.create(project=p, member=create_user, workspace=workspace, role=20)
    return p


@pytest.fixture
def estados(db, projeto, workspace):
    return {
        grupo: State.objects.create(name=grupo, project=projeto, workspace=workspace, group=grupo)
        for grupo in ("unstarted", "started", "completed", "cancelled")
    }


@pytest.fixture
def etapas(db, workspace, create_user):
    """O arranjo do seed: um destino por balde, mais uma etapa neutra."""

    def nova(nome, **marcacoes):
        return WorkStage.objects.create(
            workspace=workspace, owner=create_user, name=nome, color="#000", group="backlog", **marcacoes
        )

    return {
        "recentes": nova("Recentes", is_default=True, automation_disabled=True),
        "andamento": nova("Em Andamento"),
        "hoje": nova("Para Hoje", is_due_today=True),
        "vencidas": nova("Pendências", is_overdue=True, automation_disabled=True),
        "amanha": nova("Para amanhã", is_due_tomorrow=True),
        "depois": nova("Para Depois", is_due_later=True),
    }


def cria_tarefa(projeto, workspace, create_user, estado, vencimento, sequencia):
    tarefa = Issue.objects.create(
        name=f"t{sequencia}",
        project=projeto,
        workspace=workspace,
        state=estado,
        target_date=vencimento,
        sequence_id=sequencia,
    )
    # `.assignees.add()` não serve: o through-model exige projeto e workspace,
    # e o atalho do Django os deixa nulos.
    IssueAssignee.objects.create(
        issue=tarefa, assignee=create_user, project=projeto, workspace=workspace
    )
    return tarefa


def onde_esta(tarefa, create_user):
    linha = WorkStageIssue.objects.filter(issue=tarefa, owner=create_user).first()
    return linha.stage.name if linha else None


@pytest.mark.contract
class TestOBaldeDeCadaData:
    """A conta pura, sem banco: é ela que define o produto."""

    @pytest.mark.parametrize(
        "vencimento,esperado",
        [
            (HOJE - timedelta(days=1), "vencidas"),
            (HOJE - timedelta(days=90), "vencidas"),
            (HOJE, "hoje"),
            (HOJE + timedelta(days=1), "amanha"),
            # O limite que o pedido original deixava ambíguo: D+2 é "depois",
            # e não um dia órfão entre amanhã e depois.
            (HOJE + timedelta(days=2), "depois"),
            (HOJE + timedelta(days=365), "depois"),
        ],
    )
    def test_cada_data_cai_no_balde_certo(self, vencimento, esperado):
        assert balde_da_tarefa(vencimento, HOJE) == esperado

    def test_sem_vencimento_vai_para_hoje(self):
        """Conceito do produto, não caso de borda: tarefa sem data é esquecida."""
        assert balde_da_tarefa(None, HOJE) == "hoje"


@pytest.mark.contract
@pytest.mark.django_db
class TestAVarredura:
    def test_move_para_o_balde_do_vencimento(self, workspace, create_user, projeto, estados, etapas):
        vencida = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE - timedelta(days=3), 1)
        de_hoje = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE, 2)
        amanha = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE + timedelta(days=1), 3)
        depois = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE + timedelta(days=2), 4)
        # A tarefa começa na etapa neutra, e não na travada, para poder sair.
        for t in (vencida, de_hoje, amanha, depois):
            WorkStageIssue.objects.create(
                workspace=workspace, owner=create_user, issue=t, stage=etapas["andamento"]
            )

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(vencida, create_user) == "Pendências"
        assert onde_esta(de_hoje, create_user) == "Para Hoje"
        assert onde_esta(amanha, create_user) == "Para amanhã"
        assert onde_esta(depois, create_user) == "Para Depois"

    def test_sem_vencimento_vai_para_hoje_e_CONTINUA_sem_vencimento(
        self, workspace, create_user, projeto, estados, etapas
    ):
        """A afirmação que sustenta o conceito.

        Se a varredura carimbasse "hoje" ao mover, a tarefa esquecida viraria uma
        tarefa de hoje como outra qualquer — e o lembrete se apagaria no mesmo
        gesto que o criou.
        """
        tarefa = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], None, 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["andamento"]
        )

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(tarefa, create_user) == "Para Hoje"
        tarefa.refresh_from_db()
        assert tarefa.target_date is None, "a varredura carimbou data"

    def test_nunca_altera_vencimento_de_ninguem(self, workspace, create_user, projeto, estados, etapas):
        """Nem para as tarefas que TÊM data: quem escreve data é a pessoa."""
        vencida = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE - timedelta(days=3), 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=vencida, stage=etapas["andamento"]
        )

        varrer(workspace.id, create_user.id, HOJE)

        vencida.refresh_from_db()
        assert vencida.target_date == HOJE - timedelta(days=3)

    def test_rodar_duas_vezes_nao_muda_nada(self, workspace, create_user, projeto, estados, etapas):
        """Idempotência: é ela que permite o marcador ser só recuperação."""
        tarefa = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE, 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["andamento"]
        )

        primeira = varrer(workspace.id, create_user.id, HOJE)
        segunda = varrer(workspace.id, create_user.id, HOJE)

        assert primeira == 1
        assert segunda == 0
        assert onde_esta(tarefa, create_user) == "Para Hoje"


@pytest.mark.contract
@pytest.mark.django_db
class TestOQueAVarreduraNaoToca:
    @pytest.mark.parametrize("grupo", ["completed", "cancelled"])
    def test_concluida_e_cancelada_ficam_onde_estao(
        self, workspace, create_user, projeto, estados, etapas, grupo
    ):
        """Trava do motor, e não caixa que alguém precisa achar e marcar.

        Uma tarefa concluída ontem está tecnicamente vencida; movê-la para
        Pendências seria ressuscitar trabalho terminado.
        """
        tarefa = cria_tarefa(projeto, workspace, create_user, estados[grupo], HOJE - timedelta(days=5), 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["andamento"]
        )

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(tarefa, create_user) == "Em Andamento"

    def test_etapa_travada_nao_SOLTA_tarefa(self, workspace, create_user, projeto, estados, etapas):
        tarefa = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE, 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["vencidas"]
        )

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(tarefa, create_user) == "Pendências"

    def test_etapa_travada_CONTINUA_RECEBENDO(self, workspace, create_user, projeto, estados, etapas):
        """A afirmação que o resto do desenho depende.

        Pendências é destino das vencidas E a etapa mais travada. Se o opt-out
        bloqueasse a chegada, ela nunca receberia nada e ninguém entenderia por
        quê — o sintoma seria uma etapa vazia, sem erro em lugar nenhum.
        """
        vencida = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE - timedelta(days=2), 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=vencida, stage=etapas["andamento"]
        )

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(vencida, create_user) == "Pendências"

    def test_tarefa_na_etapa_padrao_travada_nao_sai(self, workspace, create_user, projeto, estados, etapas):
        """Sem linha de associação, a tarefa pertence à padrão — que é travada."""
        tarefa = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE, 1)

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(tarefa, create_user) is None, "saiu de Recentes, que está travada"

    def test_balde_sem_etapa_marcada_nao_move(self, workspace, create_user, projeto, estados, etapas):
        """As quatro marcações são opcionais, ao contrário da etapa padrão."""
        etapas["amanha"].is_due_tomorrow = False
        etapas["amanha"].save()
        tarefa = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE + timedelta(days=1), 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["andamento"]
        )

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(tarefa, create_user) == "Em Andamento"

    def test_sem_marcacao_nenhuma_a_varredura_nao_faz_nada(
        self, workspace, create_user, projeto, estados, etapas
    ):
        """Sem isto, mover tudo para a padrão passaria em vários testes acima."""
        WorkStage.objects.filter(workspace=workspace, owner=create_user).update(
            is_due_today=False, is_due_tomorrow=False, is_due_later=False, is_overdue=False
        )
        tarefa = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE, 1)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["andamento"]
        )

        assert varrer(workspace.id, create_user.id, HOJE) == 0
        assert onde_esta(tarefa, create_user) == "Em Andamento"


@pytest.mark.contract
@pytest.mark.django_db
class TestUmaEtapaParaVariosBaldes:
    def test_a_mesma_etapa_recebe_dois_baldes(self, workspace, create_user, projeto, estados, etapas):
        """"Futuro" sendo amanhã e depois é escolha legítima."""
        # A ordem importa: a constraint impede duas etapas no mesmo balde, então
        # a antiga solta antes de a nova assumir. Inverter aqui estoura — e é
        # exatamente a constraint fazendo o trabalho dela.
        etapas["depois"].is_due_later = False
        etapas["depois"].save()
        etapas["amanha"].is_due_later = True
        etapas["amanha"].name = "Futuro"
        etapas["amanha"].save()

        amanha = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE + timedelta(days=1), 1)
        depois = cria_tarefa(projeto, workspace, create_user, estados["unstarted"], HOJE + timedelta(days=9), 2)
        for t in (amanha, depois):
            WorkStageIssue.objects.create(
                workspace=workspace, owner=create_user, issue=t, stage=etapas["andamento"]
            )

        varrer(workspace.id, create_user.id, HOJE)

        assert onde_esta(amanha, create_user) == "Futuro"
        assert onde_esta(depois, create_user) == "Futuro"
