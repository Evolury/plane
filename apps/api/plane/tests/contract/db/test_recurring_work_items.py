# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Motor de recorrência (ADR 0010, revisão 13/08/2026).

O que se fixa aqui é a agenda, a cópia e o ciclo de vida da origem — as coisas
que, erradas, só aparecem semanas depois, quando a tarefa não nasceu, nasceu em
dobro, ou nasceu vencida.
"""

from datetime import date, datetime, time
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from plane.bgtasks.recurring_work_item_task import (
    agendar_apos_conclusao,
    agendar_proxima_data,
    generate_recurring_work_items,
    processar_regra,
)
from plane.db.models import (
    GenerationMode,
    Issue,
    IssueAssignee,
    Project,
    ProjectMember,
    RecurrenceEndMode,
    RecurrenceFrequency,
    RecurringSubtaskSchedule,
    RecurringWorkItem,
    RecurringWorkItemOccurrence,
    State,
    SubtaskDueAnchor,
    User,
)
from plane.db.models.recurring_work_item import MonthlyMode
from plane.utils.recurrence import proxima_data, proximas_datas
from plane.utils.subtask_tree import TETO_DE_SUBTAREFAS

SP = ZoneInfo("America/Sao_Paulo")
UTC = ZoneInfo("UTC")

# Custo marginal de cada subtarefa copiada, medido em 14/08/2026: 8, que é o
# preço de `Issue.save()` e não nosso — ponto de salvamento, trava do projeto,
# duas agregações, o insert e a linha da sequência. É o piso, e o número está
# colado nele de propósito: teto frouxo passa com o defeito (lição da F6.2).
# Ler os vínculos nó a nó, como era antes, somaria dois e estouraria aqui.
_CONSULTAS_POR_NO = 8


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(
        name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user, timezone="America/Sao_Paulo"
    )
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    State.objects.filter(project=projeto).delete()
    State.objects.create(
        name="Em espera", group="backlog", project=projeto, workspace=workspace, color="#000", default=True
    )
    State.objects.create(name="Concluído", group="completed", project=projeto, workspace=workspace, color="#000")
    return projeto


def _origem(projeto, create_user, **campos):
    padrao = dict(
        name="Relatório semanal",
        project=projeto,
        workspace=projeto.workspace,
        created_by=create_user,
    )
    padrao.update(campos)
    return Issue.objects.create(**padrao)


def _regra(projeto, create_user, origem=None, **campos):
    if origem is None:
        origem = _origem(projeto, create_user)
    padrao = dict(
        source_issue=origem,
        frequency=RecurrenceFrequency.WEEKLY,
        interval=1,
        weekdays=[1],  # segunda; a semana do produto começa no domingo
        time_of_day=time(8, 0),
        start_date=date(2026, 8, 3),
        project=projeto,
        workspace=projeto.workspace,
        created_by=create_user,
    )
    padrao.update(campos)
    return RecurringWorkItem.objects.create(**padrao)


def _subtarefa(projeto, create_user, pai, nome, **campos):
    padrao = dict(
        project=projeto, workspace=projeto.workspace, parent=pai, name=nome, created_by=create_user
    )
    padrao.update(campos)
    return Issue.objects.create(**padrao)


def _descendentes(raiz):
    """Toda a árvore abaixo de uma tarefa, em qualquer profundidade."""
    encontrados, fronteira = [], [raiz.id]
    while fronteira:
        filhas = list(Issue.issue_objects.filter(parent_id__in=fronteira).order_by("sort_order", "created_at"))
        encontrados += filhas
        fronteira = [filha.id for filha in filhas]
    return encontrados


def _arvore(raiz):
    """A árvore como dicionário aninhado de nomes — lê como desenho."""
    filhas = Issue.issue_objects.filter(parent=raiz).order_by("sort_order", "created_at")
    return {filha.name: _arvore(filha) for filha in filhas}


def _concluir(tarefa):
    tarefa.state = State.objects.get(project=tarefa.project, group="completed")
    tarefa.save(update_fields=["state"])
    return tarefa


def _em_sp(ano, mes, dia, hora=8, minuto=0):
    return datetime(ano, mes, dia, hora, minuto, tzinfo=SP)


@pytest.mark.contract
class TestAgenda:
    @pytest.mark.django_db
    def test_weekly_lands_on_the_chosen_weekday(self, projeto, create_user):
        regra = _regra(projeto, create_user)

        datas = proximas_datas(regra, _em_sp(2026, 8, 13), quantidade=3)

        assert [d.astimezone(SP).date() for d in datas] == [date(2026, 8, 17), date(2026, 8, 24), date(2026, 8, 31)]
        assert all(d.astimezone(SP).hour == 8 for d in datas)

    @pytest.mark.django_db
    def test_weekly_with_several_days_in_one_rule(self, projeto, create_user):
        """Segunda, quarta e sexta é UMA regra, não três."""
        regra = _regra(projeto, create_user, weekdays=[1, 3, 5])

        datas = proximas_datas(regra, _em_sp(2026, 8, 13), quantidade=3)

        assert [d.astimezone(SP).date() for d in datas] == [date(2026, 8, 14), date(2026, 8, 17), date(2026, 8, 19)]

    @pytest.mark.django_db
    def test_fortnightly_is_weekly_with_interval_two(self, projeto, create_user):
        regra = _regra(projeto, create_user, interval=2)

        datas = proximas_datas(regra, _em_sp(2026, 8, 13), quantidade=2)

        assert [d.astimezone(SP).date() for d in datas] == [date(2026, 8, 17), date(2026, 8, 31)]

    @pytest.mark.django_db
    def test_monthly_on_the_31st_falls_back_to_the_last_day(self, projeto, create_user):
        """O ponto do ADR 0010: quem pede dia 31 quer dizer "fim do mês".

        A RFC 5545 mandaria PULAR fevereiro, abril, junho, setembro e novembro —
        cinco meses por ano sem tarefa, e ninguém relacionaria à causa.
        """
        regra = _regra(
            projeto,
            create_user,
            frequency=RecurrenceFrequency.MONTHLY,
            monthly_mode=MonthlyMode.DAY_OF_MONTH,
            day_of_month=31,
            start_date=date(2026, 1, 31),
        )

        datas = proximas_datas(regra, _em_sp(2026, 1, 1), quantidade=4)

        assert [d.astimezone(SP).date() for d in datas] == [
            date(2026, 1, 31),
            date(2026, 2, 28),
            date(2026, 3, 31),
            date(2026, 4, 30),
        ]

    @pytest.mark.django_db
    def test_monthly_by_day_does_not_drift(self, projeto, create_user):
        """Depois de encurtar em fevereiro, março volta a ser 31.

        Somar mês a mês faria 31/01 virar 28/02 e depois 28/03, perdendo o dia
        que a pessoa pediu — por isso cada data sai do início, não da anterior.
        """
        regra = _regra(
            projeto,
            create_user,
            frequency=RecurrenceFrequency.MONTHLY,
            monthly_mode=MonthlyMode.DAY_OF_MONTH,
            day_of_month=31,
            start_date=date(2026, 1, 31),
        )

        datas = proximas_datas(regra, _em_sp(2026, 2, 1), quantidade=2)

        assert [d.astimezone(SP).date() for d in datas] == [date(2026, 2, 28), date(2026, 3, 31)]

    @pytest.mark.django_db
    def test_monthly_on_the_last_friday(self, projeto, create_user):
        regra = _regra(
            projeto,
            create_user,
            frequency=RecurrenceFrequency.MONTHLY,
            monthly_mode=MonthlyMode.WEEKDAY_OF_MONTH,
            week_of_month=-1,
            weekday_of_month=5,  # sexta
            start_date=date(2026, 8, 1),
        )

        datas = proximas_datas(regra, _em_sp(2026, 8, 1), quantidade=2)

        assert [d.astimezone(SP).date() for d in datas] == [date(2026, 8, 28), date(2026, 9, 25)]

    @pytest.mark.django_db
    def test_yearly_on_february_29_falls_back_to_28(self, projeto, create_user):
        regra = _regra(
            projeto,
            create_user,
            frequency=RecurrenceFrequency.YEARLY,
            day_of_month=29,
            month_of_year=2,
            start_date=date(2028, 2, 29),
        )

        datas = proximas_datas(regra, _em_sp(2028, 1, 1), quantidade=2)

        assert [d.astimezone(SP).date() for d in datas] == [date(2028, 2, 29), date(2029, 2, 28)]

    @pytest.mark.django_db
    def test_never_generates_before_the_start_date(self, projeto, create_user):
        regra = _regra(projeto, create_user, start_date=date(2026, 9, 7))

        datas = proximas_datas(regra, _em_sp(2026, 8, 13), quantidade=1)

        assert [d.astimezone(SP).date() for d in datas] == [date(2026, 9, 7)]

    @pytest.mark.django_db
    def test_end_on_date_stops_the_series(self, projeto, create_user):
        regra = _regra(
            projeto, create_user, end_mode=RecurrenceEndMode.ON_DATE, end_date=date(2026, 8, 20)
        )

        datas = proximas_datas(regra, _em_sp(2026, 8, 13), quantidade=5)

        assert [d.astimezone(SP).date() for d in datas] == [date(2026, 8, 17)]

    @pytest.mark.django_db
    def test_end_after_count_stops_the_series(self, projeto, create_user):
        regra = _regra(
            projeto,
            create_user,
            end_mode=RecurrenceEndMode.AFTER_COUNT,
            end_after_count=2,
            occurrences_created=2,
        )

        assert proxima_data(regra, _em_sp(2026, 8, 13)) is None

    @pytest.mark.django_db
    def test_after_completion_mode_has_no_schedule(self, projeto, create_user):
        """Nesse modo a data sai da conclusão, não do calendário."""
        regra = _regra(projeto, create_user, generation_mode=GenerationMode.AFTER_COMPLETION, days_after_completion=15)

        assert proxima_data(regra, _em_sp(2026, 8, 13)) is None
        assert proximas_datas(regra, _em_sp(2026, 8, 13)) == []


@pytest.mark.contract
class TestGeracao:
    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_copies_the_source_work_item(self, _atividade, projeto, create_user):
        """A tarefa É o molde: nome, prioridade e responsáveis vêm dela."""
        origem = _origem(projeto, create_user, priority="high", description_html="<p>como fazer</p>")
        _concluir(origem)
        IssueAssignee.objects.create(
            issue=origem, assignee=create_user, project=projeto, workspace=projeto.workspace
        )
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert tarefa is not None
        assert tarefa.name == "Relatório semanal"
        assert tarefa.priority == "high"
        assert tarefa.description_html == "<p>como fazer</p>"
        assert tarefa.state.default is True
        assert list(tarefa.assignees.all()) == [create_user]
        assert RecurringWorkItemOccurrence.objects.filter(recurring_work_item=regra, issue=tarefa).count() == 1

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_an_inactive_assignee_is_dropped_from_the_copy(self, _atividade, projeto, create_user):
        """Quem saiu do projeto não carimba as ocorrências futuras.

        Remover alguém só desativa o vínculo — as atribuições sobrevivem na
        origem. Sem o filtro, a série viraria fábrica de dono inexistente, e
        trabalho com aparência de dono é pior que sem dono (ADR 0010).
        """
        saiu = User.objects.create(email="saiu@evolury.com.br", username="saiu")
        vinculo = ProjectMember.objects.create(project=projeto, member=saiu, role=15, is_active=True)
        origem = _origem(projeto, create_user)
        for pessoa in (create_user, saiu):
            IssueAssignee.objects.create(
                issue=origem, assignee=pessoa, project=projeto, workspace=projeto.workspace
            )
        _concluir(origem)
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        vinculo.is_active = False
        vinculo.save(update_fields=["is_active"])
        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert list(tarefa.assignees.all()) == [create_user]
        # E a origem continua como está: consertar a raiz é decisão de gente.
        assert IssueAssignee.objects.filter(issue=origem).count() == 2

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_project_default_assignee_catches_the_orphan(self, _atividade, projeto, create_user):
        """Origem sem responsável cai no padrão do projeto, como qualquer tarefa.

        A regra vale em toda tarefa criada à mão; ignorá-la nas que nascem
        sozinhas deixaria sem rede justamente onde ninguém está olhando.
        """
        padrao = User.objects.create(email="padrao@evolury.com.br", username="padrao")
        ProjectMember.objects.create(project=projeto, member=padrao, role=15, is_active=True)
        projeto.default_assignee = padrao
        projeto.save(update_fields=["default_assignee"])

        origem = _concluir(_origem(projeto, create_user))  # sem responsável
        filha = Issue.objects.create(
            project=projeto, workspace=projeto.workspace, parent=origem, name="Parte", created_by=create_user
        )
        regra = _regra(projeto, create_user, origem=origem)
        regra.project.refresh_from_db()
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert list(tarefa.assignees.all()) == [padrao]
        # Subtarefa não: sem responsável nela é normal, e carimbar todas com a
        # mesma pessoa seria ruído.
        assert Issue.objects.get(parent=tarefa, name="Parte").assignees.count() == 0
        assert filha.assignees.count() == 0

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_default_assignee_never_overrides_a_real_one(self, _atividade, projeto, create_user):
        """O padrão é rede de segurança, não regra de sobreposição."""
        padrao = User.objects.create(email="padrao@evolury.com.br", username="padrao")
        ProjectMember.objects.create(project=projeto, member=padrao, role=15, is_active=True)
        projeto.default_assignee = padrao
        projeto.save(update_fields=["default_assignee"])

        origem = _origem(projeto, create_user)
        IssueAssignee.objects.create(
            issue=origem, assignee=create_user, project=projeto, workspace=projeto.workspace
        )
        _concluir(origem)
        regra = _regra(projeto, create_user, origem=origem)
        regra.project.refresh_from_db()
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert list(tarefa.assignees.all()) == [create_user]

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_an_inactive_default_assignee_is_ignored(self, _atividade, projeto, create_user):
        """Padrão que saiu do projeto não pode voltar pela porta dos fundos."""
        padrao = User.objects.create(email="padrao@evolury.com.br", username="padrao")
        vinculo = ProjectMember.objects.create(project=projeto, member=padrao, role=15, is_active=True)
        projeto.default_assignee = padrao
        projeto.save(update_fields=["default_assignee"])
        vinculo.is_active = False
        vinculo.save(update_fields=["is_active"])

        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        regra.project.refresh_from_db()
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert tarefa.assignees.count() == 0

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_default_assignee_catches_what_the_ghost_left(self, _atividade, projeto, create_user):
        """As duas regras juntas: descarta o fantasma, o padrão assume."""
        saiu = User.objects.create(email="saiu@evolury.com.br", username="saiu")
        vinculo = ProjectMember.objects.create(project=projeto, member=saiu, role=15, is_active=True)
        padrao = User.objects.create(email="padrao@evolury.com.br", username="padrao")
        ProjectMember.objects.create(project=projeto, member=padrao, role=15, is_active=True)
        projeto.default_assignee = padrao
        projeto.save(update_fields=["default_assignee"])

        origem = _origem(projeto, create_user)
        IssueAssignee.objects.create(
            issue=origem, assignee=saiu, project=projeto, workspace=projeto.workspace
        )
        _concluir(origem)
        regra = _regra(projeto, create_user, origem=origem)
        regra.project.refresh_from_db()
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        vinculo.is_active = False
        vinculo.save(update_fields=["is_active"])
        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert list(tarefa.assignees.all()) == [padrao]

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_dates_are_calculated_never_copied(self, _atividade, projeto, create_user):
        """Nasce hoje, vence na data da agenda — nada herdado da origem."""
        origem = _origem(projeto, create_user, start_date=date(2026, 1, 1), target_date=date(2026, 1, 5))
        _concluir(origem)
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert tarefa.start_date == date(2026, 8, 17)
        assert tarefa.target_date == date(2026, 8, 17)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_lead_time_creates_before_the_due_date(self, _atividade, projeto, create_user):
        """A antecedência: nasce em D-3 com início D-3 e vencimento D."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem, lead_time_days=3)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 8, 17)

        # Quatro dias antes ainda não dispara.
        assert processar_regra(regra, agora=_em_sp(2026, 8, 13, 8, 0)) is None

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 14, 8, 5))

        assert tarefa is not None
        assert tarefa.start_date == date(2026, 8, 14)
        assert tarefa.target_date == date(2026, 8, 17)
        regra.refresh_from_db()
        # E o relógio vai para a semana seguinte — não fica preso na data
        # ainda futura, tentando gerá-la de novo a cada rodada.
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 8, 24)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_lead_time_in_hours_fires_within_the_day(self, _atividade, projeto, create_user):
        """Horas são o preparo: a pauta chega 2 horas antes da reunião."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem, lead_time_hours=2)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        assert regra.next_run_at.astimezone(SP) == _em_sp(2026, 8, 17, 8, 0)

        # Três horas antes ainda não dispara; duas, sim.
        assert processar_regra(regra, agora=_em_sp(2026, 8, 17, 5, 0)) is None
        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 6, 5))

        assert tarefa is not None
        assert tarefa.start_date == date(2026, 8, 17)
        assert tarefa.target_date == date(2026, 8, 17)
        regra.refresh_from_db()
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 8, 24)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_job_window_counts_hours_in_sql(self, _atividade, projeto, create_user):
        """A janela do job soma dias e horas no banco, não só em Python."""
        from datetime import timedelta

        from django.utils import timezone

        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem, lead_time_hours=2)
        # Vence daqui a uma hora; com duas de antecedência, já é devida.
        RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=timezone.now() + timedelta(hours=1))

        generate_recurring_work_items()

        assert RecurringWorkItemOccurrence.objects.filter(recurring_work_item=regra).count() == 1

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_subtasks_come_along_open_and_dateless(self, _atividade, projeto, create_user):
        """Abertas e sem data — data ausente não mente (ADR 0010)."""
        origem = _origem(projeto, create_user)
        filha = Issue.objects.create(
            project=projeto,
            workspace=projeto.workspace,
            parent=origem,
            name="Separar os números",
            start_date=date(2026, 8, 1),
            target_date=date(2026, 8, 2),
            created_by=create_user,
        )
        _concluir(filha)
        _concluir(origem)
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        copias = Issue.objects.filter(parent=tarefa)
        assert [c.name for c in copias] == ["Separar os números"]
        copia = copias.get()
        assert copia.start_date is None and copia.target_date is None
        assert copia.state.group == "backlog"  # aberta, mesmo com a original concluída

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_whole_subtask_tree_comes_along(self, _atividade, projeto, create_user):
        """A hierarquia descreve o trabalho, então acompanha inteira (F8).

        O recorte no primeiro nível entregava a ocorrência com o passo grande e
        sem os passos dele — e a falta era invisível, porque o cartão da origem
        continua mostrando a árvore toda.
        """
        origem = _concluir(_origem(projeto, create_user))
        filha = _subtarefa(projeto, create_user, origem, "Fechar o caixa")
        neta = _subtarefa(projeto, create_user, filha, "Conferir extrato")
        _subtarefa(projeto, create_user, neta, "Anexar comprovantes")
        _subtarefa(projeto, create_user, origem, "Enviar por e-mail")
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert _arvore(tarefa) == {
            "Fechar o caixa": {"Conferir extrato": {"Anexar comprovantes": {}}},
            "Enviar por e-mail": {},
        }

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_cap_counts_the_whole_tree(self, _atividade, projeto, create_user):
        """O teto conta a árvore, não os filhos diretos.

        Sem isto, "50 subtarefas" viraria 50 × 50 no dia em que o aninhamento
        entrasse — a ocorrência deixaria de ser tarefa e viraria projeto.

        E o corte respeita a hierarquia: ninguém é copiado sem o pai, senão a
        ocorrência nasceria com ramo solto pendurado na raiz.
        """
        origem = _concluir(_origem(projeto, create_user))
        for i in range(10):
            pai = _subtarefa(projeto, create_user, origem, f"Etapa {i}", sort_order=i)
            for j in range(9):
                _subtarefa(projeto, create_user, pai, f"Passo {i}.{j}", sort_order=j)
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        copiadas = _descendentes(tarefa)
        assert len(copiadas) == TETO_DE_SUBTAREFAS
        ids = {copia.id for copia in copiadas} | {tarefa.id}
        assert all(copia.parent_id in ids for copia in copiadas)
        # Largura: os 10 primeiros níveis rasos entram antes de qualquer neto.
        assert len([c for c in copiadas if c.parent_id == tarefa.id]) == 10

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_cycle_in_the_parent_chain_does_not_hang(self, _atividade, projeto, create_user):
        """`parent` é ponteiro comum: nada no banco impede A → B → A.

        Numa travessia ingênua isso seria laço infinito dentro de um job de
        fundo — o lugar onde ninguém está olhando quando trava.
        """
        origem = _concluir(_origem(projeto, create_user))
        a = _subtarefa(projeto, create_user, origem, "A")
        b = _subtarefa(projeto, create_user, a, "B")
        Issue.objects.filter(pk=origem.pk).update(parent=b)
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert sorted(c.name for c in _descendentes(tarefa)) == ["A", "B"]

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_an_archived_branch_is_skipped_whole(self, _atividade, projeto, create_user):
        """Arquivar um ramo tira o ramo, não só o nó.

        A neta continua visível para o banco; copiá-la penduraria na raiz uma
        tarefa cujo contexto — o pai arquivado — não veio junto.
        """
        origem = _concluir(_origem(projeto, create_user))
        arquivada = _subtarefa(projeto, create_user, origem, "Ramo arquivado")
        _subtarefa(projeto, create_user, arquivada, "Neta do arquivado")
        _subtarefa(projeto, create_user, origem, "Ramo vivo")
        Issue.objects.filter(pk=arquivada.pk).update(archived_at=date(2026, 8, 10))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert [c.name for c in _descendentes(tarefa)] == ["Ramo vivo"]

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_nested_subtask_can_declare_its_own_due_date(self, _atividade, projeto, create_user):
        """O vencimento relativo (F7) vale em qualquer profundidade.

        Se valesse só no primeiro nível, a árvore entraria na cópia e metade
        dela ficaria sem o recurso — a inconsistência que ninguém lê no manual
        e descobre configurando.
        """
        origem = _concluir(_origem(projeto, create_user))
        filha = _subtarefa(projeto, create_user, origem, "Fechar o caixa")
        neta = _subtarefa(projeto, create_user, filha, "Conferir extrato")
        regra = _regra(projeto, create_user, origem=origem, lead_time_days=3)
        RecurringSubtaskSchedule.objects.create(
            recurring_work_item=regra, subtask=neta, anchor=SubtaskDueAnchor.BEFORE_DUE, offset_days=1
        )
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 14, 8, 5))

        copias = {c.name: c for c in _descendentes(tarefa)}
        assert copias["Conferir extrato"].target_date == date(2026, 8, 16)
        assert copias["Fechar o caixa"].target_date is None

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_tree_does_not_cost_a_query_per_node(
        self, _atividade, projeto, create_user, django_assert_max_num_queries
    ):
        """Responsáveis, etiquetas e agendas vêm em bloco, não nó a nó.

        O custo da geração foi o motivo declarado de a subtarefa aninhada ter
        ficado para o ciclo seguinte (ADR 0010) — então ele é o que se fixa.

        O teste mede o custo **marginal**: quanto uma árvore de 16 nós custa a
        mais que uma de 4. Criar tarefa tem preço fixo e irredutível (trava de
        projeto, duas agregações, a linha da sequência), e é por isso que um
        teto absoluto aqui seria frouxo o bastante para passar com o defeito.
        O que não pode voltar é a consulta de vínculos por nó.
        """

        def _com_arvore(nome, ramos, folhas):
            origem = _concluir(_origem(projeto, create_user, name=nome))
            for i in range(ramos):
                pai = _subtarefa(projeto, create_user, origem, f"{nome} {i}")
                for j in range(folhas):
                    _subtarefa(projeto, create_user, pai, f"{nome} {i}.{j}")
            regra = _regra(projeto, create_user, origem=origem)
            agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
            regra.refresh_from_db()
            return regra

        rasa = _com_arvore("Rasa", 2, 1)  # 4 nós
        funda = _com_arvore("Funda", 4, 3)  # 16 nós

        with django_assert_max_num_queries(1000) as pequena:
            processar_regra(rasa, agora=_em_sp(2026, 8, 17, 8, 5))
        with django_assert_max_num_queries(1000) as grande:
            processar_regra(funda, agora=_em_sp(2026, 8, 17, 8, 5))

        por_no = (len(grande.captured_queries) - len(pequena.captured_queries)) / 12
        assert por_no <= _CONSULTAS_POR_NO

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_subtask_can_have_its_own_relative_due_date(self, _atividade, projeto, create_user):
        """As duas âncoras, dentro da janela que a antecedência abre.

        Nasce em 14/08 (3 dias de antecedência) e vence em 17/08: "1 dia após o
        nascimento" cai em 15/08, "2 dias antes do vencimento" cai em 15/08
        também — âncoras diferentes que aqui coincidem de propósito, para o
        teste provar que cada uma calcula pela sua ponta.
        """
        origem = _concluir(_origem(projeto, create_user))
        preparo = Issue.objects.create(
            project=projeto, workspace=projeto.workspace, parent=origem, name="Reunir dados",
            created_by=create_user, sort_order=1,
        )
        revisao = Issue.objects.create(
            project=projeto, workspace=projeto.workspace, parent=origem, name="Revisar",
            created_by=create_user, sort_order=2,
        )
        Issue.objects.create(
            project=projeto, workspace=projeto.workspace, parent=origem, name="Sem prazo",
            created_by=create_user, sort_order=3,
        )
        regra = _regra(projeto, create_user, origem=origem, lead_time_days=3)
        RecurringSubtaskSchedule.objects.create(
            recurring_work_item=regra, subtask=preparo, anchor=SubtaskDueAnchor.AFTER_CREATION, offset_days=1
        )
        RecurringSubtaskSchedule.objects.create(
            recurring_work_item=regra, subtask=revisao, anchor=SubtaskDueAnchor.BEFORE_DUE, offset_days=2
        )
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 14, 8, 5))

        assert (tarefa.start_date, tarefa.target_date) == (date(2026, 8, 14), date(2026, 8, 17))
        copias = {c.name: c for c in Issue.objects.filter(parent=tarefa)}
        assert copias["Reunir dados"].target_date == date(2026, 8, 15)
        assert copias["Revisar"].target_date == date(2026, 8, 15)
        # Sem agenda continua sem data: ausência é escolha legítima.
        assert copias["Sem prazo"].target_date is None

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_subtask_never_is_born_already_overdue(self, _atividade, projeto, create_user):
        """Deslocamento maior que a janela é recortado no nascimento.

        "10 dias antes do vencimento" numa ocorrência que nasce no mesmo dia em
        que vence cairia 10 dias no passado — a subtarefa nasceria vencida, que
        é exatamente o defeito do Asana que a F4 evitou não copiando datas.
        """
        origem = _concluir(_origem(projeto, create_user))
        filha = Issue.objects.create(
            project=projeto, workspace=projeto.workspace, parent=origem, name="Revisar",
            created_by=create_user,
        )
        regra = _regra(projeto, create_user, origem=origem)  # sem antecedência
        RecurringSubtaskSchedule.objects.create(
            recurring_work_item=regra, subtask=filha, anchor=SubtaskDueAnchor.BEFORE_DUE, offset_days=10
        )
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert Issue.objects.get(parent=tarefa).target_date == tarefa.start_date == date(2026, 8, 17)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_subtask_schedule_is_recomputed_every_cycle(self, _atividade, projeto, create_user):
        """Cada ciclo calcula do zero — nada é deslocado.

        É o que nos livra do defeito do ClickUp, cujo remapeamento não funciona
        quando a data do pai recua: aqui não existe data anterior para mover.
        """
        origem = _concluir(_origem(projeto, create_user))
        filha = Issue.objects.create(
            project=projeto, workspace=projeto.workspace, parent=origem, name="Revisar",
            created_by=create_user,
        )
        regra = _regra(projeto, create_user, origem=origem, lead_time_days=2)
        RecurringSubtaskSchedule.objects.create(
            recurring_work_item=regra, subtask=filha, anchor=SubtaskDueAnchor.BEFORE_DUE, offset_days=1
        )
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        primeira = processar_regra(regra, agora=_em_sp(2026, 8, 15, 8, 5))
        _concluir(primeira)
        regra.refresh_from_db()
        segunda = processar_regra(regra, agora=_em_sp(2026, 8, 22, 8, 5))

        assert Issue.objects.get(parent=primeira).target_date == date(2026, 8, 16)
        assert Issue.objects.get(parent=segunda).target_date == date(2026, 8, 23)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_skipped_date_does_not_generate_and_the_series_goes_on(
        self, _atividade, projeto, create_user
    ):
        """Pular é exceção a uma ocorrência, não à agenda (ADR 0010, F9).

        A prova de que a série não foi mexida está na segunda rodada: a semana
        seguinte nasce no dia de sempre. Se pular adiantasse ou atrasasse o
        relógio, seria edição de agenda disfarçada de exceção.
        """
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        RecurringWorkItemOccurrence.objects.create(
            recurring_work_item=regra,
            workspace=projeto.workspace,
            scheduled_for=regra.next_run_at,
            skipped_at=timezone.now(),
        )

        pulada = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        regra.refresh_from_db()
        seguinte = processar_regra(regra, agora=_em_sp(2026, 8, 24, 8, 5))

        assert pulada is None
        assert seguinte is not None and seguinte.target_date == date(2026, 8, 24)
        # O contador conta trabalho criado, e pulo não é trabalho.
        regra.refresh_from_db()
        assert regra.occurrences_created == 1

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_skipped_date_does_not_hold_the_open_guard(self, _atividade, projeto, create_user):
        """A linha do pulo não tem tarefa, e guarda de trabalho aberto lê tarefa.

        Sem isto, pular uma vez travaria a série para sempre: a guarda veria a
        linha, concluiria que há ocorrência em aberto, e nada mais nasceria.
        """
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem, skip_while_previous_open=True)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        RecurringWorkItemOccurrence.objects.create(
            recurring_work_item=regra,
            workspace=projeto.workspace,
            scheduled_for=regra.next_run_at,
            skipped_at=timezone.now(),
        )

        processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        regra.refresh_from_db()

        assert processar_regra(regra, agora=_em_sp(2026, 8, 24, 8, 5)) is not None

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_an_occurrence_without_a_work_item_is_not_a_skip(self, _atividade, projeto, create_user):
        """Linha sem tarefa não é pulo — só pulo é pulo.

        Ocorrência sem tarefa existe por outros motivos: a linha é gravada
        **antes** da tarefa, de propósito, para que dois workers na mesma regra
        esbarrem na unicidade em vez de criarem em dobro. Um processo que morra
        entre as duas gravações deixa a linha órfã.

        Sem a marca própria, `issue` nulo teria de servir de pulo, e o motor
        leria "ninguém quis esta data" onde a verdade é "algo deu errado aqui".
        """
        from plane.bgtasks.recurring_work_item_task import _foi_pulada

        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        orfa = RecurringWorkItemOccurrence.objects.create(
            recurring_work_item=regra, workspace=projeto.workspace, scheduled_for=regra.next_run_at
        )

        assert orfa.issue_id is None and orfa.skipped_at is None
        assert _foi_pulada(regra, regra.next_run_at) is False

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_running_twice_creates_one_work_item(self, _atividade, projeto, create_user):
        """Idempotência garantida pelo banco, não por confiança no relógio."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        previsto = regra.next_run_at

        processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        # Uma segunda rodada com a MESMA data prevista, como aconteceria se o
        # worker repetisse a mensagem.
        regra.refresh_from_db()
        regra.next_run_at = previsto
        processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 6))

        assert Issue.objects.filter(project=projeto, parent__isnull=True).count() == 2  # origem + 1

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_delay_does_not_pile_up(self, _atividade, projeto, create_user):
        """Job fora do ar por duas semanas gera UMA tarefa, não três."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        processar_regra(regra, agora=_em_sp(2026, 9, 2, 10, 0))

        assert Issue.objects.filter(project=projeto, parent__isnull=True).count() == 2
        regra.refresh_from_db()
        # E a próxima data é a seguinte a AGORA, não a que ficou para trás.
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 9, 7)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_the_open_source_counts_as_open_work(self, _atividade, projeto, create_user):
        """A origem é o item zero da série: aberta, a guarda segura a geração."""
        regra = _regra(projeto, create_user)  # origem na etapa padrão, aberta
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        assert processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5)) is None
        assert Issue.objects.filter(project=projeto, parent__isnull=True).count() == 1  # só a origem

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_does_not_generate_while_the_previous_is_open(self, _atividade, projeto, create_user):
        """A resposta ao quadro entupido de cópias da mesma coisa."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        regra.refresh_from_db()
        processar_regra(regra, agora=_em_sp(2026, 8, 24, 8, 5))

        assert Issue.objects.filter(project=projeto, parent__isnull=True).count() == 2

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_deleted_occurrence_does_not_hold_the_guard(self, _atividade, projeto, create_user):
        """Excluída não é aberta: ninguém a vê no quadro para entender o bloqueio."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        primeira = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        primeira.delete()  # exclusão lógica, aberta

        regra.refresh_from_db()
        segunda = processar_regra(regra, agora=_em_sp(2026, 8, 24, 8, 5))

        assert segunda is not None

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_completing_before_the_due_moment_rescues_the_period(self, _atividade, projeto, create_user):
        """Concluída em cima da hora, a ocorrência do período ainda nasce.

        O ponto de virada da guarda é o VENCIMENTO, não o disparo: antes dele,
        liberar a guarda gera com a antecedência que restou; depois dele, o
        período é pulado (testado logo abaixo, no deslize do relógio).
        """
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem, lead_time_days=1)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        primeira = processar_regra(regra, agora=_em_sp(2026, 8, 16, 8, 5))
        assert primeira is not None  # nasceu no domingo, vence segunda 17/08

        # Domingo 23/08 (disparo da próxima): a anterior segue aberta → nada,
        # e o relógio continua apontando para 24/08.
        regra.refresh_from_db()
        assert processar_regra(regra, agora=_em_sp(2026, 8, 23, 8, 5)) is None
        regra.refresh_from_db()
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 8, 24)

        # Concluída na segunda 05:00, três horas antes de vencer: a rodada
        # seguinte resgata a ocorrência do período, com a antecedência restante.
        _concluir(primeira)
        segunda = processar_regra(regra, agora=_em_sp(2026, 8, 24, 5, 10))

        assert segunda is not None
        assert segunda.start_date == date(2026, 8, 24)
        assert segunda.target_date == date(2026, 8, 24)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_a_period_missed_while_blocked_is_skipped(self, _atividade, projeto, create_user):
        """Vencimento passado com a anterior aberta: o período não nasce vencido."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        primeira = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        # Segunda 24/08 às 10:00, anterior ainda aberta: o relógio desliza.
        regra.refresh_from_db()
        assert processar_regra(regra, agora=_em_sp(2026, 8, 24, 10, 0)) is None
        regra.refresh_from_db()
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 8, 31)

        # Concluir às 11:00 não ressuscita o período perdido.
        _concluir(primeira)
        assert processar_regra(regra, agora=_em_sp(2026, 8, 24, 11, 0)) is None
        assert (
            RecurringWorkItemOccurrence.objects.filter(recurring_work_item=regra).count() == 1
        )

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_generates_again_once_the_previous_is_closed(self, _atividade, projeto, create_user):
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        primeira = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        _concluir(primeira)

        regra.refresh_from_db()
        segunda = processar_regra(regra, agora=_em_sp(2026, 8, 24, 8, 5))

        assert segunda is not None
        assert Issue.objects.filter(project=projeto, parent__isnull=True).count() == 3

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_inactive_rule_generates_nothing(self, _atividade, projeto, create_user):
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem, is_active=False)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        assert processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5)) is None
        assert Issue.objects.filter(project=projeto, parent__isnull=True).count() == 1


@pytest.mark.contract
class TestCicloDeVidaDaOrigem:
    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_archived_source_pauses_the_rule(self, _atividade, projeto, create_user):
        """Arquivar pausa: nada é gerado, e o relógio desliza para o futuro."""
        origem = _concluir(_origem(projeto, create_user))
        origem.archived_at = date(2026, 8, 16)
        origem.save(update_fields=["archived_at"])
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        assert processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5)) is None
        assert Issue.objects.filter(project=projeto, parent__isnull=True).count() == 1
        regra.refresh_from_db()
        # Desarquivar retoma da próxima data — sem despejar o período perdido.
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 8, 24)
        assert regra.is_active is True

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_deleted_source_deletes_the_rule(self, _atividade, projeto, create_user):
        """Excluir a origem exclui a regra — o job é a rede de segurança."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        origem.delete()  # exclusão lógica, como na interface

        assert processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5)) is None
        assert RecurringWorkItem.objects.filter(pk=regra.pk).count() == 0


@pytest.mark.contract
class TestUltimoDiaEAposConclusao:
    @pytest.mark.django_db
    def test_last_day_of_month_is_an_option_of_its_own(self, projeto, create_user):
        """Ninguém pensa "dia 31" quando quer dizer "fecha o mês"."""
        regra = _regra(
            projeto,
            create_user,
            frequency=RecurrenceFrequency.MONTHLY,
            monthly_mode=MonthlyMode.LAST_DAY,
            start_date=date(2026, 1, 1),
        )

        datas = proximas_datas(regra, _em_sp(2026, 1, 1), quantidade=4)

        assert [d.astimezone(SP).date() for d in datas] == [
            date(2026, 1, 31),
            date(2026, 2, 28),
            date(2026, 3, 31),
            date(2026, 4, 30),
        ]

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_completing_the_source_starts_the_series(self, _atividade, projeto, create_user):
        """A agenda desse modo não está no calendário, está na conclusão.

        A origem é o item zero: concluí-la marca a primeira ocorrência.
        """
        regra = _regra(
            projeto,
            create_user,
            generation_mode=GenerationMode.AFTER_COMPLETION,
            days_after_completion=15,
            start_date=date(2026, 8, 17),
        )
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 17, 8, 0))
        # Enquanto ninguém concluir a origem, não há data nenhuma.
        assert regra.next_run_at is None

        concluido = State.objects.get(project=projeto, group="completed")
        _concluir(regra.source_issue)
        with mock.patch("django.utils.timezone.now", return_value=_em_sp(2026, 8, 20, 10, 0)):
            agendar_apos_conclusao(issue_id=regra.source_issue_id, novo_estado_id=concluido.id)

        regra.refresh_from_db()
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 9, 4)

        tarefa = processar_regra(regra, agora=_em_sp(2026, 9, 4, 8, 5))
        assert tarefa is not None
        regra.refresh_from_db()
        # Sem nova conclusão, não há próxima data: nada é gerado no vazio.
        assert regra.next_run_at is None

        # E concluir a ocorrência agenda a seguinte.
        _concluir(tarefa)
        with mock.patch("django.utils.timezone.now", return_value=_em_sp(2026, 9, 10, 10, 0)):
            agendar_apos_conclusao(issue_id=tarefa.id, novo_estado_id=concluido.id)

        regra.refresh_from_db()
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 9, 25)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_late_completion_does_not_skip_a_period(self, _atividade, projeto, create_user):
        """O defeito conhecido do Asana: concluir com atraso pulava um mês.

        Aqui a data nova conta a partir da conclusão, então atrasar EMPURRA a
        próxima — nunca some com ela.
        """
        regra = _regra(
            projeto,
            create_user,
            generation_mode=GenerationMode.AFTER_COMPLETION,
            days_after_completion=30,
            start_date=date(2026, 8, 1),
        )
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 1, 8, 0))

        concluido = State.objects.get(project=projeto, group="completed")
        _concluir(regra.source_issue)
        # Concluída com três dias de atraso sobre o planejado.
        with mock.patch("django.utils.timezone.now", return_value=_em_sp(2026, 9, 3, 9, 0)):
            agendar_apos_conclusao(issue_id=regra.source_issue_id, novo_estado_id=concluido.id)

        regra.refresh_from_db()
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 10, 3)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_completing_a_scheduled_occurrence_does_not_move_the_clock(
        self, _atividade, projeto, create_user
    ):
        """No modo por agenda, concluir não mexe na agenda."""
        origem = _concluir(_origem(projeto, create_user))
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        regra.refresh_from_db()
        antes = regra.next_run_at

        concluido = State.objects.get(project=projeto, group="completed")
        agendar_apos_conclusao(issue_id=tarefa.id, novo_estado_id=concluido.id)

        regra.refresh_from_db()
        assert regra.next_run_at == antes
