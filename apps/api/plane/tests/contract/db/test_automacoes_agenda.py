# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Automações agendadas e as ações de voz (ADR 0012, F2).

O que estes testes fixam é o que, quebrando, produz o mesmo defeito de sempre:
uma regra que parece configurada e não faz nada — ou que faz demais.

No relógio, dois riscos concretos e conhecidos da recorrência:

- **atraso que acumula**: um dia de fila fora do ar viraria uma rodada por dia
  perdido, todas de uma vez;
- **data no passado**: faria o job rodar em laço a cada tique até alcançar o
  presente.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from plane.bgtasks.automation_task import TETO_POR_RODADA, executar_agendada, rodar_automacoes_agendadas
from plane.db.models import (
    Automation,
    AutomationRun,
    AutomationRunStatus,
    AutomationTrigger,
    Cycle,
    CycleIssue,
    EmailNotificationLog,
    Issue,
    IssueComment,
    Notification,
    Project,
    ProjectMember,
    State,
)
from plane.utils.automacoes.agenda import proxima_execucao, reagendar
from plane.utils.automacoes.variaveis import aplicar
from plane.utils.automacoes.validacao import validar_acoes, validar_gatilho

SP = ZoneInfo("America/Sao_Paulo")


@pytest.fixture
def projeto(workspace, create_user):
    projeto = Project.objects.create(
        name="Agenda", identifier="AGD", workspace=workspace, project_lead=create_user, timezone="America/Sao_Paulo"
    )
    ProjectMember.objects.create(project=projeto, workspace=workspace, member=create_user, role=20)
    return projeto


@pytest.fixture
def estados(projeto, workspace):
    State.objects.filter(project=projeto).delete()
    return {
        "aberta": State.objects.create(
            name="Aberta", group="unstarted", project=projeto, workspace=workspace, color="#000"
        ),
        "feito": State.objects.create(
            name="Feito", group="completed", project=projeto, workspace=workspace, color="#0a0"
        ),
    }


def _tarefa(projeto, workspace, estado, nome="Tarefa", **campos):
    return Issue.objects.create(name=nome, project=projeto, workspace=workspace, state=estado, **campos)


def _agendada(projeto, workspace, config=None, acoes=None, condicao=None):
    return Automation.objects.create(
        project=projeto,
        workspace=workspace,
        name="Varredura",
        trigger_type=AutomationTrigger.SCHEDULED,
        trigger_config=config or {"frequency": "daily", "time": "08:00", "weekdays": []},
        condition=condicao,
        actions=acoes or [],
    )


@pytest.mark.contract
class TestRelogio:
    @pytest.mark.django_db
    def test_proxima_execucao_e_sempre_no_futuro(self, projeto, workspace):
        """Data no passado faria o job rodar em laço a cada tique."""
        regra = _agendada(projeto, workspace)
        agora = datetime(2026, 8, 16, 14, 0, tzinfo=SP)

        proxima = proxima_execucao(regra, agora)

        assert proxima > agora
        assert proxima.astimezone(SP).hour == 8

    @pytest.mark.django_db
    def test_horario_e_do_fuso_do_projeto(self, projeto, workspace):
        """"Toda manhã às 8h" tem de ser 8h de quem lê o quadro (ADR 0006)."""
        regra = _agendada(projeto, workspace, {"frequency": "daily", "time": "08:00", "weekdays": []})
        proxima = proxima_execucao(regra, datetime(2026, 8, 16, 9, 0, tzinfo=SP))

        assert proxima.astimezone(SP).strftime("%H:%M") == "08:00"
        # Em UTC o mesmo instante é 11:00 — o que prova que não guardamos "8h UTC".
        assert proxima.astimezone(ZoneInfo("UTC")).hour == 11

    @pytest.mark.django_db
    def test_semanal_cai_num_dia_escolhido(self, projeto, workspace):
        # 1 = segunda, na contagem do produto (0 = domingo, ADR 0005)
        regra = _agendada(projeto, workspace, {"frequency": "weekly", "time": "08:00", "weekdays": [1]})
        # 16/08/2026 é um domingo
        proxima = proxima_execucao(regra, datetime(2026, 8, 16, 12, 0, tzinfo=SP))

        local = proxima.astimezone(SP)
        assert local.strftime("%A") == "Monday"
        assert local.day == 17

    @pytest.mark.django_db
    def test_semanal_sem_dia_escolhido_vale_todo_dia(self, projeto, workspace):
        """Lista vazia é "todos", nunca "nenhum" — nenhum seria regra muda."""
        regra = _agendada(projeto, workspace, {"frequency": "weekly", "time": "08:00", "weekdays": []})
        proxima = proxima_execucao(regra, datetime(2026, 8, 16, 12, 0, tzinfo=SP))

        assert proxima.astimezone(SP).day == 17

    @pytest.mark.django_db
    def test_atraso_nao_acumula(self, projeto, workspace, estados):
        """Vencida há dois dias roda UMA vez e é reagendada para a frente."""
        regra = _agendada(projeto, workspace, acoes=[{"type": "archive", "config": {}}])
        Automation.objects.filter(pk=regra.pk).update(next_run_at=timezone.now() - timedelta(days=2))
        regra.refresh_from_db()

        rodar_automacoes_agendadas()

        regra.refresh_from_db()
        assert AutomationRun.objects.filter(automation=regra).count() == 1
        assert regra.next_run_at > timezone.now()

    @pytest.mark.django_db
    def test_regra_de_evento_nao_ganha_relogio(self, projeto, workspace):
        regra = Automation.objects.create(
            project=projeto,
            workspace=workspace,
            name="Por evento",
            trigger_type=AutomationTrigger.FIELD_CHANGED,
            trigger_config={"field": "priority"},
            actions=[],
        )
        assert reagendar(regra) is None
        regra.refresh_from_db()
        assert regra.next_run_at is None


@pytest.mark.contract
class TestExecucaoEmLote:
    @pytest.mark.django_db
    def test_roda_sobre_todas_as_tarefas_que_casam(self, projeto, workspace, estados):
        _tarefa(projeto, workspace, estados["feito"], "Uma")
        _tarefa(projeto, workspace, estados["feito"], "Outra")
        _tarefa(projeto, workspace, estados["aberta"], "Aberta")

        regra = _agendada(
            projeto,
            workspace,
            acoes=[{"type": "archive", "config": {}}],
            condicao={"state_id": [str(estados["feito"].id)]},
        )
        executar_agendada(regra)

        assert Issue.objects.filter(project=projeto, archived_at__isnull=False).count() == 2
        # Uma linha para a rodada inteira, não uma por tarefa.
        assert AutomationRun.objects.filter(automation=regra).count() == 1

    @pytest.mark.django_db
    def test_o_corte_por_teto_aparece_no_registro(self, projeto, workspace, estados, monkeypatch):
        """Truncar em silêncio faria a regra parecer ter agido em tudo."""
        monkeypatch.setattr("plane.bgtasks.automation_task.TETO_POR_RODADA", 1)
        _tarefa(projeto, workspace, estados["feito"], "Uma")
        _tarefa(projeto, workspace, estados["feito"], "Outra")

        regra = _agendada(projeto, workspace, acoes=[{"type": "archive", "config": {}}])
        executar_agendada(regra)

        detalhes = [r["detalhe"] for r in AutomationRun.objects.get(automation=regra).actions_result]
        assert any("primeiras 1" in d for d in detalhes)

    @pytest.mark.django_db
    def test_teto_por_rodada_e_um_numero_de_verdade(self):
        """Guarda contra alguém zerar o teto sem querer."""
        assert TETO_POR_RODADA >= 1


@pytest.mark.contract
class TestVariaveis:
    @pytest.mark.django_db
    def test_troca_o_que_conhece(self, projeto, workspace, estados):
        tarefa = _tarefa(projeto, workspace, estados["aberta"], "Trocar o disco")
        texto = aplicar("A tarefa {{tarefa}} está em {{estado}}.", tarefa, {})
        assert texto == "A tarefa Trocar o disco está em Aberta."

    @pytest.mark.django_db
    def test_variavel_desconhecida_fica_literal(self, projeto, workspace, estados):
        """Ver o que se escreveu é melhor do que ver um comentário sumir."""
        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        assert aplicar("valor {{orcamento}}", tarefa, {}) == "valor {{orcamento}}"

    @pytest.mark.django_db
    def test_vencimento_vazio_nao_quebra(self, projeto, workspace, estados):
        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        assert aplicar("vence {{vencimento}}", tarefa, {}) == "vence —"


@pytest.mark.contract
class TestAcoesDaVoz:
    @pytest.mark.django_db
    def test_comentario_escapa_marcacao(self, projeto, workspace, estados, create_user):
        """Uma regra não pode virar injeção de marcação na tela de quem lê."""
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        contexto = {
            "ator_id": ator_da_automacao(workspace.id).id,
            "automacao": regra,
            "evento": {},
            "profundidade": 0,
        }

        executar("add_comment", tarefa, {"text": "<script>alert(1)</script>"}, contexto)

        comentario = IssueComment.objects.get(issue=tarefa)
        assert "<script>" not in comentario.comment_html
        assert "&lt;script&gt;" in comentario.comment_html

    @pytest.mark.django_db
    def test_notificar_cria_sino_e_fila_de_email(self, projeto, workspace, estados, create_user):
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        contexto = {
            "ator_id": ator_da_automacao(workspace.id).id,
            "automacao": regra,
            "evento": {},
            "profundidade": 0,
        }

        resultado = executar("notify", tarefa, {"users": [str(create_user.id)], "text": "Olha isto"}, contexto)

        assert resultado["status"] == "aplicada"
        assert Notification.objects.filter(receiver=create_user).count() == 1
        assert EmailNotificationLog.objects.filter(receiver=create_user).count() == 1

    @pytest.mark.django_db
    def test_o_email_do_aviso_e_montavel(self, projeto, workspace, estados, create_user):
        """A fila de e-mail descarta, em SILÊNCIO, registro sem `issue_activity`.

        Sem isto a linha entrava na fila e o e-mail saía vazio: o aviso aparecia
        no sino e não chegava à caixa de entrada — que é exatamente o caso de
        quem não está com o produto aberto, e o motivo de a ação existir.
        """
        from plane.bgtasks.email_notification_task import create_payload
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        robo = ator_da_automacao(workspace.id)
        contexto = {"ator_id": robo.id, "automacao": regra, "evento": {}, "profundidade": 0}

        executar("notify", tarefa, {"users": [str(create_user.id)], "text": "Olha isto"}, contexto)

        registro = EmailNotificationLog.objects.get(receiver=create_user)
        montado = create_payload({str(robo.id): [registro.data]})

        assert montado[str(robo.id)]["automation"]["new_value"] == ["Olha isto"]
        # A montagem faz `pop` de `activity_time` sem padrão — a ausência
        # derrubaria o envio do lote inteiro, e não só desta linha.
        assert "activity_time" in montado[str(robo.id)]

    @pytest.mark.django_db
    def test_notificar_sem_ninguem_nao_grava(self, projeto, workspace, estados):
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        contexto = {
            "ator_id": ator_da_automacao(workspace.id).id,
            "automacao": regra,
            "evento": {},
            "profundidade": 0,
        }

        resultado = executar("notify", tarefa, {"users": [], "especiais": ["assignees"]}, contexto)

        assert resultado["status"] == "sem_efeito"
        assert Notification.objects.count() == 0

    @pytest.mark.django_db
    def test_modulo_usa_o_id_escolhido_na_regra(self, projeto, workspace, estados, create_user):
        """Aqui o id fixo é a resposta certa, ao contrário do ciclo.

        A assimetria é do domínio: um ciclo é sprint que termina, um módulo é
        contêiner durável. O que se escolhe hoje continua certo em seis meses.
        """
        from plane.db.models import Module, ModuleIssue
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        modulo = Module.objects.create(
            name="Autenticação", project=projeto, workspace=workspace, lead=create_user
        )
        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        contexto = {
            "ator_id": ator_da_automacao(workspace.id).id,
            "automacao": regra,
            "evento": {},
            "profundidade": 0,
        }

        resultado = executar("add_to_module", tarefa, {"module_id": str(modulo.id)}, contexto)

        assert resultado["status"] == "aplicada"
        assert ModuleIssue.objects.get(issue=tarefa, deleted_at__isnull=True).module_id == modulo.id

    @pytest.mark.django_db
    def test_modulo_apagado_nao_derruba_a_regra(self, projeto, workspace, estados):
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        contexto = {
            "ator_id": ator_da_automacao(workspace.id).id,
            "automacao": regra,
            "evento": {},
            "profundidade": 0,
        }

        resultado = executar(
            "add_to_module", tarefa, {"module_id": "00000000-0000-0000-0000-000000000000"}, contexto
        )

        assert resultado["status"] == "sem_efeito"
        assert "não existe mais" in resultado["detalhe"]

    @pytest.mark.django_db
    def test_arquivar_recusa_tarefa_em_andamento(self, projeto, workspace, estados):
        """Arquivar trabalho não terminado faria sumir da tela o que ninguém acabou."""
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        contexto = {
            "ator_id": ator_da_automacao(workspace.id).id,
            "automacao": regra,
            "evento": {},
            "profundidade": 0,
        }

        resultado = executar("archive", tarefa, {}, contexto)

        tarefa.refresh_from_db()
        assert resultado["status"] == "sem_efeito"
        assert tarefa.archived_at is None

    @pytest.mark.django_db
    def test_ciclo_usa_o_ativo_e_nao_um_id_fixo(self, projeto, workspace, estados, create_user):
        from plane.utils.automacoes.acoes import executar
        from plane.utils.automacoes.ator import ator_da_automacao

        agora = timezone.now()
        Cycle.objects.create(
            name="Encerrado",
            project=projeto,
            workspace=workspace,
            owned_by=create_user,
            start_date=agora - timedelta(days=30),
            end_date=agora - timedelta(days=15),
        )
        ativo = Cycle.objects.create(
            name="Atual",
            project=projeto,
            workspace=workspace,
            owned_by=create_user,
            start_date=agora - timedelta(days=1),
            end_date=agora + timedelta(days=10),
        )

        tarefa = _tarefa(projeto, workspace, estados["aberta"])
        regra = _agendada(projeto, workspace)
        contexto = {
            "ator_id": ator_da_automacao(workspace.id).id,
            "automacao": regra,
            "evento": {},
            "profundidade": 0,
        }

        executar("add_to_cycle", tarefa, {}, contexto)

        assert CycleIssue.objects.get(issue=tarefa, deleted_at__isnull=True).cycle_id == ativo.id


@pytest.mark.contract
class TestValidacaoDaF2:
    @pytest.mark.django_db
    def test_agendada_agora_e_aceita(self, projeto):
        config = validar_gatilho(
            "scheduled", {"frequency": "weekly", "time": "9:30", "weekdays": [1, 3]}, ["scheduled"], projeto.id
        )
        assert config["frequency"] == "weekly"
        assert config["weekdays"] == [1, 3]

    @pytest.mark.django_db
    def test_horario_malformado_e_recusado(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_gatilho("scheduled", {"time": "manhã"}, ["scheduled"], projeto.id)
        assert "HH:MM" in str(erro.value)

    @pytest.mark.django_db
    def test_dia_da_semana_fora_da_faixa_e_recusado(self, projeto):
        with pytest.raises(Exception):
            validar_gatilho("scheduled", {"frequency": "weekly", "weekdays": [9]}, ["scheduled"], projeto.id)

    @pytest.mark.django_db
    def test_comentario_vazio_e_recusado(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_acoes([{"type": "add_comment", "config": {"text": "   "}}], projeto.id)
        assert "texto do comentário" in str(erro.value)

    @pytest.mark.django_db
    def test_notificar_sem_destinatario_e_recusado(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_acoes([{"type": "notify", "config": {}}], projeto.id)
        assert "quem será avisado" in str(erro.value)

    @pytest.mark.django_db
    def test_arquivar_e_ciclo_nao_pedem_configuracao(self, projeto):
        validado = validar_acoes(
            [{"type": "archive", "config": {}}, {"type": "add_to_cycle", "config": {}}], projeto.id
        )
        assert [a["type"] for a in validado] == ["archive", "add_to_cycle"]
