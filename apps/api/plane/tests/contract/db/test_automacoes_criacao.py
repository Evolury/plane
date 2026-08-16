# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Criação de tarefa e subtarefa por automação (ADR 0012, F3).

O defeito número um deste recurso, nos produtos que o têm, **não é laço
infinito — é duplicata**: a Asana tem o relato de checklist criado em dobro
quando a regra dispara duas vezes, e o Jira o de clone duplicado porque a
criação chega a levantar o evento mais de uma vez.

Por isso a metade destes testes é sobre idempotência, e por isso a garantia mora
no banco (unicidade em regra + origem + nome), e não na confiança de que o motor
roda uma vez só.

A outra metade fixa a fronteira com Tarefas recorrentes (ADR 0010), que é
divisão de propósito e não sobreposição: a agenda cuida da rotina, o evento
cuida da reação.
"""

import pytest

from plane.bgtasks.automation_task import executar_automacao
from plane.db.models import (
    Automation,
    AutomationCreation,
    AutomationRunStatus,
    AutomationTrigger,
    Issue,
    IssueAssignee,
    Project,
    ProjectMember,
    RecurringWorkItem,
    State,
)
from plane.utils.automacoes.acoes import SEM_EFEITO, executar
from plane.utils.automacoes.ator import ator_da_automacao
from plane.utils.automacoes.gatilhos import automacao_casa
from plane.utils.automacoes.validacao import validar_acoes


@pytest.fixture
def projeto(workspace, create_user):
    projeto = Project.objects.create(
        name="Criação", identifier="CRI", workspace=workspace, project_lead=create_user
    )
    ProjectMember.objects.create(project=projeto, workspace=workspace, member=create_user, role=20)
    return projeto


@pytest.fixture
def estado(projeto, workspace):
    State.objects.filter(project=projeto).delete()
    return State.objects.create(
        name="A fazer", group="unstarted", project=projeto, workspace=workspace, color="#000", default=True
    )


def _tarefa(projeto, workspace, estado, nome="Origem"):
    return Issue.objects.create(name=nome, project=projeto, workspace=workspace, state=estado)


def _regra(projeto, workspace, acoes, gatilho=AutomationTrigger.FIELD_CHANGED, **campos):
    return Automation.objects.create(
        project=projeto,
        workspace=workspace,
        name="Regra",
        trigger_type=gatilho,
        trigger_config={"field": "state_id"} if gatilho == AutomationTrigger.FIELD_CHANGED else {},
        actions=acoes,
        **campos,
    )


def _contexto(regra, workspace):
    return {
        "ator_id": ator_da_automacao(workspace.id).id,
        "automacao": regra,
        "evento": {},
        "profundidade": 0,
    }


@pytest.mark.contract
class TestIdempotencia:
    """A metade que existe por causa da reclamação real do mercado."""

    @pytest.mark.django_db
    def test_disparar_duas_vezes_nao_duplica_o_checklist(self, projeto, workspace, estado):
        """É literalmente o defeito relatado na Asana."""
        origem = _tarefa(projeto, workspace, estado)
        regra = _regra(
            projeto,
            workspace,
            [{"type": "create_subtasks", "config": {"names": ["Conferir", "Assinar", "Arquivar"]}}],
        )

        executar_automacao(regra, origem, {"tipo": "alterada", "mudancas": []})
        executar_automacao(regra, origem, {"tipo": "alterada", "mudancas": []})

        assert Issue.objects.filter(parent=origem).count() == 3

    @pytest.mark.django_db
    def test_segunda_execucao_diz_por_que_nao_fez_nada(self, projeto, workspace, estado):
        origem = _tarefa(projeto, workspace, estado)
        regra = _regra(projeto, workspace, [{"type": "create_subtasks", "config": {"names": ["Conferir"]}}])
        contexto = _contexto(regra, workspace)

        executar("create_subtasks", origem, {"names": ["Conferir"]}, contexto)
        segundo = executar("create_subtasks", origem, {"names": ["Conferir"]}, contexto)

        assert segundo["status"] == SEM_EFEITO
        assert "já tinham sido criadas" in segundo["detalhe"]

    @pytest.mark.django_db
    def test_item_novo_na_regra_e_criado_sozinho(self, projeto, workspace, estado):
        """Acrescentar um item e disparar de novo cria só o item novo."""
        origem = _tarefa(projeto, workspace, estado)
        regra = _regra(projeto, workspace, [])
        contexto = _contexto(regra, workspace)

        executar("create_subtasks", origem, {"names": ["Conferir"]}, contexto)
        segundo = executar("create_subtasks", origem, {"names": ["Conferir", "Assinar"]}, contexto)

        assert Issue.objects.filter(parent=origem).count() == 2
        assert "Assinar" in segundo["detalhe"]

    @pytest.mark.django_db
    def test_a_garantia_esta_no_banco(self, projeto, workspace, estado):
        """Unicidade em (regra, origem, nome) — não em confiança no motor."""
        from django.db.utils import IntegrityError

        origem = _tarefa(projeto, workspace, estado)
        regra = _regra(projeto, workspace, [])
        AutomationCreation.objects.create(
            automation=regra, workspace=workspace, source_issue=origem, chave="Conferir"
        )
        with pytest.raises(IntegrityError):
            AutomationCreation.objects.create(
                automation=regra, workspace=workspace, source_issue=origem, chave="Conferir"
            )

    @pytest.mark.django_db
    def test_outra_origem_ganha_o_proprio_checklist(self, projeto, workspace, estado):
        """A chave é por ORIGEM: outra tarefa recebe o seu."""
        regra = _regra(projeto, workspace, [])
        contexto = _contexto(regra, workspace)
        uma = _tarefa(projeto, workspace, estado, "Uma")
        outra = _tarefa(projeto, workspace, estado, "Outra")

        executar("create_subtasks", uma, {"names": ["Conferir"]}, contexto)
        executar("create_subtasks", outra, {"names": ["Conferir"]}, contexto)

        assert Issue.objects.filter(parent=uma).count() == 1
        assert Issue.objects.filter(parent=outra).count() == 1


@pytest.mark.contract
class TestFronteiraComRecorrencia:
    """Divisão de propósito: a agenda cuida da rotina, o evento da reação."""

    @pytest.mark.django_db
    def test_agendado_mais_criar_e_recusado_ao_salvar(self, projeto):
        """A combinação não existe — e a recusa é ao salvar, não num aviso."""
        with pytest.raises(Exception) as erro:
            validar_acoes(
                [{"type": "create_work_item", "config": {"name": "X"}}], projeto.id, trigger_type="scheduled"
            )
        assert "Tarefas recorrentes" in str(erro.value)

    @pytest.mark.django_db
    def test_a_mesma_acao_e_aceita_em_gatilho_de_evento(self, projeto):
        validadas = validar_acoes(
            [{"type": "create_work_item", "config": {"name": "X"}}], projeto.id, trigger_type="field_changed"
        )
        assert validadas[0]["type"] == "create_work_item"

    @pytest.mark.django_db
    def test_tarefa_criada_nao_ganha_recorrencia(self, projeto, workspace, estado, create_user):
        """Nem própria, nem herdada da origem."""
        origem = _tarefa(projeto, workspace, estado)
        RecurringWorkItem.objects.create(
            source_issue=origem,
            project=projeto,
            workspace=workspace,
            frequency="daily",
            time_of_day="08:00",
            start_date="2026-08-01",
        )
        regra = _regra(projeto, workspace, [])
        executar("create_work_item", origem, {"name": "Acompanhar"}, _contexto(regra, workspace))

        nova = Issue.objects.get(name="Acompanhar")
        assert RecurringWorkItem.objects.filter(source_issue=nova).count() == 0

    @pytest.mark.django_db
    def test_subtarefa_em_molde_de_recorrencia_e_recusada(self, projeto, workspace, estado):
        """Mexer no molde muda TODAS as ocorrências futuras — é o defeito da Asana."""
        molde = _tarefa(projeto, workspace, estado, "Molde")
        RecurringWorkItem.objects.create(
            source_issue=molde,
            project=projeto,
            workspace=workspace,
            frequency="daily",
            time_of_day="08:00",
            start_date="2026-08-01",
            is_active=True,
        )
        regra = _regra(projeto, workspace, [])

        resultado = executar("create_subtasks", molde, {"names": ["Conferir"]}, _contexto(regra, workspace))

        assert resultado["status"] == SEM_EFEITO
        assert "recorrência ativa" in resultado["detalhe"]
        assert Issue.objects.filter(parent=molde).count() == 0

    @pytest.mark.django_db
    def test_ocorrencia_de_recorrencia_nao_dispara_regra_de_criacao(self, projeto, workspace):
        """Padrão desligado, como Notion e ClickUp fazem explicitamente."""
        regra = _regra(projeto, workspace, [], gatilho=AutomationTrigger.WORK_ITEM_CREATED)
        evento = {"tipo": "criada", "de_recorrencia": True}

        assert automacao_casa(regra, evento) is False

    @pytest.mark.django_db
    def test_o_interruptor_liga_para_quem_quiser(self, projeto, workspace):
        regra = _regra(
            projeto, workspace, [], gatilho=AutomationTrigger.WORK_ITEM_CREATED, include_recurring=True
        )
        evento = {"tipo": "criada", "de_recorrencia": True}

        assert automacao_casa(regra, evento) is True

    @pytest.mark.django_db
    def test_tarefa_comum_dispara_normalmente(self, projeto, workspace):
        """A separação não pode virar silêncio para o caminho normal."""
        regra = _regra(projeto, workspace, [], gatilho=AutomationTrigger.WORK_ITEM_CREATED)

        assert automacao_casa(regra, {"tipo": "criada", "de_recorrencia": False}) is True
        assert automacao_casa(regra, {"tipo": "criada"}) is True


@pytest.mark.contract
class TestComportamentoDaCriacao:
    @pytest.mark.django_db
    def test_nasce_na_etapa_padrao_do_projeto(self, projeto, workspace, workspace_estado=None):
        """Nunca na etapa da origem — a instância que reaparece em "Concluído"
        é o defeito mais reclamado do Asana, e o ADR 0010 já o registrou."""
        State.objects.filter(project=projeto).delete()
        padrao = State.objects.create(
            name="Entrada", group="unstarted", project=projeto, workspace=workspace, color="#000", default=True
        )
        feito = State.objects.create(
            name="Feito", group="completed", project=projeto, workspace=workspace, color="#0a0"
        )
        origem = Issue.objects.create(name="Origem", project=projeto, workspace=workspace, state=feito)
        regra = _regra(projeto, workspace, [])

        executar("create_work_item", origem, {"name": "Acompanhar"}, _contexto(regra, workspace))

        assert Issue.objects.get(name="Acompanhar").state_id == padrao.id

    @pytest.mark.django_db
    def test_herda_responsaveis_quando_a_regra_pede(self, projeto, workspace, estado, create_user):
        origem = _tarefa(projeto, workspace, estado)
        IssueAssignee.objects.create(
            issue=origem, assignee=create_user, project=projeto, workspace=workspace
        )
        regra = _regra(projeto, workspace, [])

        executar(
            "create_subtasks",
            origem,
            {"names": ["Conferir"], "herdar_responsaveis": True},
            _contexto(regra, workspace),
        )

        filha = Issue.objects.get(parent=origem)
        assert list(filha.issue_assignee.values_list("assignee_id", flat=True)) == [create_user.id]

    @pytest.mark.django_db
    def test_sem_herdar_a_subtarefa_nasce_sem_responsavel(self, projeto, workspace, estado, create_user):
        origem = _tarefa(projeto, workspace, estado)
        IssueAssignee.objects.create(
            issue=origem, assignee=create_user, project=projeto, workspace=workspace
        )
        regra = _regra(projeto, workspace, [])

        executar("create_subtasks", origem, {"names": ["Conferir"]}, _contexto(regra, workspace))

        assert Issue.objects.get(parent=origem).issue_assignee.count() == 0

    @pytest.mark.django_db
    def test_vencimento_relativo_ao_dia_da_criacao(self, projeto, workspace, estado):
        """Relativo, nunca fixo: "em 3 dias" continua certo no mês que vem."""
        from datetime import timedelta

        from django.utils import timezone

        origem = _tarefa(projeto, workspace, estado)
        regra = _regra(projeto, workspace, [])

        executar(
            "create_work_item", origem, {"name": "Acompanhar", "due_in_days": 3}, _contexto(regra, workspace)
        )

        esperado = timezone.localtime().date() + timedelta(days=3)
        assert Issue.objects.get(name="Acompanhar").target_date == esperado

    @pytest.mark.django_db
    def test_a_tarefa_criada_e_assinada_pelo_robo(self, projeto, workspace, estado):
        """`BaseModel.save` reescreve `created_by` a partir do usuário da
        requisição, e no worker não há requisição. Sem passar a autoria pelo
        `save`, a tarefa nascia sem autor — o robô assinava as alterações e não
        as criações, que é a metade que mais interessa aqui."""
        origem = _tarefa(projeto, workspace, estado)
        regra = _regra(projeto, workspace, [])
        robo = ator_da_automacao(workspace.id)

        executar("create_work_item", origem, {"name": "Acompanhar"}, _contexto(regra, workspace))

        assert Issue.objects.get(name="Acompanhar").created_by_id == robo.id

    @pytest.mark.django_db
    def test_o_nome_aceita_variaveis(self, projeto, workspace, estado):
        origem = _tarefa(projeto, workspace, estado, "Contrato ACME")
        regra = _regra(projeto, workspace, [])

        executar("create_work_item", origem, {"name": "Revisar {{tarefa}}"}, _contexto(regra, workspace))

        assert Issue.objects.filter(name="Revisar Contrato ACME").exists()

    @pytest.mark.django_db
    def test_criacao_entra_no_registro_de_execucoes(self, projeto, workspace, estado):
        origem = _tarefa(projeto, workspace, estado)
        regra = _regra(
            projeto, workspace, [{"type": "create_subtasks", "config": {"names": ["Conferir", "Assinar"]}}]
        )

        status = executar_automacao(regra, origem, {"tipo": "alterada", "mudancas": []})

        assert status == AutomationRunStatus.MATCHED
        detalhe = regra.runs.first().actions_result[0]["detalhe"]
        assert "Conferir" in detalhe and "Assinar" in detalhe

    @pytest.mark.django_db
    def test_teto_de_subtarefas_por_regra(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_acoes(
                [{"type": "create_subtasks", "config": {"names": [f"item {i}" for i in range(30)]}}],
                projeto.id,
                trigger_type="field_changed",
            )
        assert "No máximo" in str(erro.value)
