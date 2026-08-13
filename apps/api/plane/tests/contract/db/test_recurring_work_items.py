# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Motor de recorrência (ADR 0010).

O que se fixa aqui é a agenda e a geração — as duas coisas que, erradas, só
aparecem semanas depois, quando a tarefa não nasceu ou nasceu em dobro.
"""

from datetime import date, datetime, time
from unittest import mock
from zoneinfo import ZoneInfo

import pytest

from plane.bgtasks.recurring_work_item_task import agendar_proxima_data, processar_regra
from plane.db.models import (
    GenerationMode,
    Issue,
    Project,
    ProjectMember,
    RecurrenceEndMode,
    RecurrenceFrequency,
    RecurringWorkItem,
    RecurringWorkItemOccurrence,
    State,
)
from plane.db.models.recurring_work_item import MonthlyMode
from plane.utils.recurrence import proxima_data, proximas_datas

SP = ZoneInfo("America/Sao_Paulo")
UTC = ZoneInfo("UTC")


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


def _regra(projeto, create_user, **campos):
    padrao = dict(
        name="Relatório semanal",
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
    def test_creates_the_work_item_from_the_template(self, _atividade, projeto, create_user):
        regra = _regra(projeto, create_user, template_priority="high")
        regra.template_assignees.add(create_user)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        assert tarefa is not None
        assert tarefa.name == "Relatório semanal"
        assert tarefa.priority == "high"
        assert tarefa.state.default is True
        assert list(tarefa.assignees.all()) == [create_user]
        assert RecurringWorkItemOccurrence.objects.filter(recurring_work_item=regra, issue=tarefa).count() == 1

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_running_twice_creates_one_work_item(self, _atividade, projeto, create_user):
        """Idempotência garantida pelo banco, não por confiança no relógio."""
        regra = _regra(projeto, create_user)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        previsto = regra.next_run_at

        processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        # Uma segunda rodada com a MESMA data prevista, como aconteceria se o
        # worker repetisse a mensagem.
        regra.refresh_from_db()
        regra.next_run_at = previsto
        processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 6))

        assert Issue.objects.filter(project=projeto).count() == 1

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_delay_does_not_pile_up(self, _atividade, projeto, create_user):
        """Job fora do ar por duas semanas gera UMA tarefa, não três."""
        regra = _regra(projeto, create_user)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        processar_regra(regra, agora=_em_sp(2026, 9, 2, 10, 0))

        assert Issue.objects.filter(project=projeto).count() == 1
        regra.refresh_from_db()
        # E a próxima data é a seguinte a AGORA, não a que ficou para trás.
        assert regra.next_run_at.astimezone(SP).date() == date(2026, 9, 7)

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_does_not_generate_while_the_previous_is_open(self, _atividade, projeto, create_user):
        """A resposta ao quadro entupido de cópias da mesma coisa."""
        regra = _regra(projeto, create_user)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        regra.refresh_from_db()
        processar_regra(regra, agora=_em_sp(2026, 8, 24, 8, 5))

        assert Issue.objects.filter(project=projeto).count() == 1

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_generates_again_once_the_previous_is_closed(self, _atividade, projeto, create_user):
        regra = _regra(projeto, create_user)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))
        primeira = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))
        primeira.state = State.objects.get(project=projeto, group="completed")
        primeira.save(update_fields=["state"])

        regra.refresh_from_db()
        segunda = processar_regra(regra, agora=_em_sp(2026, 8, 24, 8, 5))

        assert segunda is not None
        assert Issue.objects.filter(project=projeto).count() == 2

    @pytest.mark.django_db
    @mock.patch("plane.bgtasks.recurring_work_item_task.issue_activity.delay")
    def test_inactive_rule_generates_nothing(self, _atividade, projeto, create_user):
        regra = _regra(projeto, create_user, is_active=False)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        assert processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5)) is None
        assert Issue.objects.filter(project=projeto).count() == 0
