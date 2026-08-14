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
        """Um nível, abertas, sem data — data ausente não mente (ADR 0010)."""
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
        Issue.objects.create(
            project=projeto,
            workspace=projeto.workspace,
            parent=filha,
            name="Neta não entra",
            created_by=create_user,
        )
        _concluir(origem)
        regra = _regra(projeto, create_user, origem=origem)
        agendar_proxima_data(regra, a_partir_de=_em_sp(2026, 8, 13))

        tarefa = processar_regra(regra, agora=_em_sp(2026, 8, 17, 8, 5))

        copias = Issue.objects.filter(parent=tarefa)
        assert [c.name for c in copias] == ["Separar os números"]
        copia = copias.get()
        assert copia.start_date is None and copia.target_date is None
        assert copia.state.group == "backlog"  # aberta, mesmo com a original concluída
        assert Issue.objects.filter(parent=copia).count() == 0

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
