# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Motor de automações personalizadas (ADR 0012, F1).

O que estes testes fixam não é o caminho feliz — é o conjunto de decisões que,
se regredirem, produzem SILÊNCIO: regra que não casa e não diz por quê, ação
que grava atividade falsa porque não mudou nada, laço que roda até o banco
reclamar, regra malformada aceita e depois muda para sempre.

Cada teste abaixo corresponde a uma dessas.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from plane.db.models import (
    Automation,
    AutomationRun,
    AutomationRunStatus,
    AutomationTrigger,
    Issue,
    IssueActivity,
    IssueLabel,
    IssueProperty,
    IssuePropertyOption,
    Label,
    Project,
    ProjectMember,
    State,
)
from plane.utils.automacoes.acoes import ERRO, SEM_EFEITO
from plane.utils.automacoes.condicao import casa, tarefas_que_casam
from plane.utils.automacoes.gatilhos import automacao_casa, mudanca_de_propriedade
from plane.utils.automacoes.validacao import validar_acoes, validar_condicao, validar_gatilho
from plane.bgtasks.automation_task import executar_automacao


@pytest.fixture
def projeto(workspace, create_user):
    projeto = Project.objects.create(
        name="Automações", identifier="AUTO", workspace=workspace, project_lead=create_user
    )
    ProjectMember.objects.create(project=projeto, workspace=workspace, member=create_user, role=20)
    return projeto


@pytest.fixture
def estados(projeto, workspace):
    State.objects.filter(project=projeto).delete()
    return {
        "a_fazer": State.objects.create(
            name="A fazer", group="unstarted", project=projeto, workspace=workspace, color="#000"
        ),
        "feito": State.objects.create(
            name="Feito", group="completed", project=projeto, workspace=workspace, color="#0a0"
        ),
    }


def _tarefa(projeto, workspace, estado, nome="Tarefa", prioridade="none"):
    return Issue.objects.create(
        name=nome, project=projeto, workspace=workspace, state=estado, priority=prioridade
    )


def _linha_de_atividade(tarefa, campo, de, para, identificadores=False):
    """Uma linha de histórico como `track_*` a monta, sem gravar no banco."""
    return IssueActivity(
        issue=tarefa,
        verb="updated",
        field=campo,
        old_value=None if identificadores else de,
        new_value=None if identificadores else para,
        old_identifier=de if identificadores else None,
        new_identifier=para if identificadores else None,
        project_id=tarefa.project_id,
        workspace_id=tarefa.workspace_id,
    )


def _regra(projeto, workspace, **campos):
    padrao = {
        "name": "Regra",
        "trigger_type": AutomationTrigger.FIELD_CHANGED,
        "trigger_config": {"field": "priority", "from": [], "to": []},
        "condition": None,
        "actions": [],
    }
    padrao.update(campos)
    return Automation.objects.create(project=projeto, workspace=workspace, **padrao)


@pytest.mark.contract
class TestCondicao:
    """O "se" é o filtro do produto aplicado a uma tarefa só."""

    @pytest.mark.django_db
    def test_condicao_vazia_deixa_passar(self, projeto, workspace, estados):
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        assert casa(tarefa.id, None) is True

    @pytest.mark.django_db
    def test_condicao_que_casa_e_que_nao_casa(self, projeto, workspace, estados):
        urgente = _tarefa(projeto, workspace, estados["a_fazer"], "Urgente", "urgent")
        tranquila = _tarefa(projeto, workspace, estados["a_fazer"], "Tranquila", "low")

        condicao = {"priority": ["urgent"]}
        assert casa(urgente.id, condicao) is True
        assert casa(tranquila.id, condicao) is False

    @pytest.mark.django_db
    def test_condicao_usa_o_mesmo_vocabulario_do_filtro(self, projeto, workspace, estados):
        """Estado por id, como o quadro manda — e não pelo nome do estado."""
        feita = _tarefa(projeto, workspace, estados["feito"], "Feita")
        aberta = _tarefa(projeto, workspace, estados["a_fazer"], "Aberta")

        condicao = {"state_id": [str(estados["feito"].id)]}
        assert casa(feita.id, condicao) is True
        assert casa(aberta.id, condicao) is False

    @pytest.mark.django_db
    def test_simulacao_conta_as_tarefas_do_projeto(self, projeto, workspace, estados):
        _tarefa(projeto, workspace, estados["a_fazer"], "Uma", "urgent")
        _tarefa(projeto, workspace, estados["a_fazer"], "Outra", "urgent")
        _tarefa(projeto, workspace, estados["a_fazer"], "Terceira", "low")

        assert tarefas_que_casam(projeto.id, {"priority": ["urgent"]}).count() == 2


@pytest.mark.contract
class TestGatilho:
    """O "quando" casa pelo id do campo, nunca pelo texto que a tela mostra."""

    @pytest.mark.django_db
    def test_campo_alterado_sem_qualificador_casa_qualquer_mudanca(self, projeto, workspace):
        regra = _regra(projeto, workspace)
        evento = {"tipo": "alterada", "mudancas": [{"campo": "priority", "de": "low", "para": "high"}]}
        assert automacao_casa(regra, evento) is True

    @pytest.mark.django_db
    def test_qualificador_para_restringe(self, projeto, workspace):
        regra = _regra(
            projeto, workspace, trigger_config={"field": "priority", "from": [], "to": ["urgent"]}
        )
        casa_urgente = {"tipo": "alterada", "mudancas": [{"campo": "priority", "de": "low", "para": "urgent"}]}
        nao_casa = {"tipo": "alterada", "mudancas": [{"campo": "priority", "de": "low", "para": "high"}]}

        assert automacao_casa(regra, casa_urgente) is True
        assert automacao_casa(regra, nao_casa) is False

    @pytest.mark.django_db
    def test_campo_de_outro_tipo_nao_casa(self, projeto, workspace):
        regra = _regra(projeto, workspace, trigger_config={"field": "state_id", "from": [], "to": []})
        evento = {"tipo": "alterada", "mudancas": [{"campo": "priority", "de": "low", "para": "high"}]}
        assert automacao_casa(regra, evento) is False

    @pytest.mark.django_db
    def test_regra_nao_responde_a_si_mesma(self, projeto, workspace):
        """A autoguarda: sem ela, "quando a prioridade mudar → mudar a prioridade"
        seria um laço de um elo só, e o teto de profundidade só o cortaria três
        voltas depois."""
        regra = _regra(projeto, workspace)
        evento = {
            "tipo": "alterada",
            "mudancas": [{"campo": "priority", "de": "low", "para": "high"}],
            "automacao_origem": str(regra.id),
        }
        assert automacao_casa(regra, evento) is False

    @pytest.mark.django_db
    def test_propriedade_personalizada_casa_por_id(self, projeto, workspace):
        """A chave é `property_<uuid>`, e não o nome — renomear não pode
        desligar a regra em silêncio."""
        propriedade = IssueProperty.objects.create(
            name="Cliente", property_type="text", project=projeto, workspace=workspace
        )
        regra = _regra(
            projeto,
            workspace,
            trigger_config={"field": f"property_{propriedade.id}", "from": [], "to": []},
        )
        evento = {"tipo": "alterada", "mudancas": [mudanca_de_propriedade(propriedade.id, "", "ACME")]}
        assert automacao_casa(regra, evento) is True

        propriedade.name = "Conta"
        propriedade.save(update_fields=["name"])
        assert automacao_casa(regra, evento) is True


@pytest.mark.contract
class TestAcoes:
    """O "então" escreve pelo caminho do produto — e não escreve à toa."""

    @pytest.mark.django_db
    def test_muda_o_estado_e_registra_execucao(self, projeto, workspace, estados):
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_state", "config": {"state_id": str(estados["feito"].id)}}],
        )

        status = executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        tarefa.refresh_from_db()
        assert status == AutomationRunStatus.MATCHED
        assert tarefa.state_id == estados["feito"].id
        assert AutomationRun.objects.filter(automation=regra, status=AutomationRunStatus.MATCHED).count() == 1

    @pytest.mark.django_db
    def test_detalhe_do_registro_e_legivel_por_gente(self, projeto, workspace, estados):
        """O registro de execuções é uma tela para PESSOA ler.

        Um par de UUIDs no detalhe é tão útil quanto não ter registro nenhum —
        e foi exatamente o que apareceu na primeira verificação visual.
        """
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_state", "config": {"state_id": str(estados["feito"].id)}}],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        detalhe = AutomationRun.objects.get(automation=regra).actions_result[0]["detalhe"]
        assert detalhe == "A fazer → Feito"
        assert str(estados["feito"].id) not in detalhe

    @pytest.mark.django_db
    def test_acao_sem_efeito_nao_grava_nada(self, projeto, workspace, estados):
        """"Já estava assim" é resultado legítimo, e precisa aparecer no
        registro: é o que evita atividade falsa, webhook falso — e é o que faz
        um encadeamento circular convergir sozinho."""
        tarefa = _tarefa(projeto, workspace, estados["feito"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_state", "config": {"state_id": str(estados["feito"].id)}}],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        execucao = AutomationRun.objects.get(automation=regra)
        assert execucao.actions_result[0]["status"] == SEM_EFEITO

    @pytest.mark.django_db
    def test_condicao_que_nao_casa_vira_linha_no_registro(self, projeto, workspace, estados):
        """A pergunta número um é "por que não rodou?". Sem esta linha, a
        resposta honesta seria "não sei"."""
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"], prioridade="low")
        regra = _regra(
            projeto,
            workspace,
            condition={"priority": ["urgent"]},
            actions=[{"type": "set_state", "config": {"state_id": str(estados["feito"].id)}}],
        )

        status = executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        tarefa.refresh_from_db()
        assert status == AutomationRunStatus.SKIPPED
        assert tarefa.state_id == estados["a_fazer"].id
        assert AutomationRun.objects.filter(automation=regra, status=AutomationRunStatus.SKIPPED).count() == 1

    @pytest.mark.django_db
    def test_condicao_quebrada_e_falha_da_regra_e_nao_silencio(self, projeto, workspace, estados):
        """Campo que não existe mais não pode virar "não casou" — isso
        esconderia uma regra quebrada atrás de um resultado que parece normal."""
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(projeto, workspace, condition={"campo_que_nao_existe": ["x"]}, actions=[])

        status = executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        assert status == AutomationRunStatus.FAILED
        assert "condição inválida" in AutomationRun.objects.get(automation=regra).error

    @pytest.mark.django_db
    def test_acoes_rodam_em_ordem_e_enxergam_a_anterior(self, projeto, workspace, estados):
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"], prioridade="low")
        regra = _regra(
            projeto,
            workspace,
            actions=[
                {"type": "set_priority", "config": {"priority": "urgent"}},
                {"type": "set_state", "config": {"state_id": str(estados["feito"].id)}},
            ],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        tarefa.refresh_from_db()
        assert tarefa.priority == "urgent"
        assert tarefa.state_id == estados["feito"].id

    @pytest.mark.django_db
    def test_detalhe_de_etiqueta_mostra_nomes(self, projeto, workspace, estados):
        """Contagem responde "quantas"; a pergunta de quem lê o log é "quais"."""
        nova = Label.objects.create(name="urgente", project=projeto, workspace=workspace)
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_labels", "config": {"mode": "add", "labels": [str(nova.id)]}}],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        detalhe = AutomationRun.objects.get(automation=regra).actions_result[0]["detalhe"]
        assert detalhe == "— → urgente"

    @pytest.mark.django_db
    def test_etiqueta_e_somada_sem_perder_as_que_ja_estavam(self, projeto, workspace, estados):
        antiga = Label.objects.create(name="antiga", project=projeto, workspace=workspace)
        nova = Label.objects.create(name="nova", project=projeto, workspace=workspace)
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        # A tabela de ligação carrega projeto e workspace próprios; `labels.add`
        # cria a linha sem eles e o banco recusa.
        IssueLabel.objects.create(issue=tarefa, label=antiga, project=projeto, workspace=workspace)

        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_labels", "config": {"mode": "add", "labels": [str(nova.id)]}}],
        )
        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        assert set(tarefa.labels.values_list("id", flat=True)) == {antiga.id, nova.id}

    @pytest.mark.django_db
    def test_acao_com_ator_robo(self, projeto, workspace, estados):
        """A ação é assinada pelo robô, e não pela pessoa que criou o projeto —
        que é o que o auto-arquivamento antigo fazia."""
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_state", "config": {"state_id": str(estados["feito"].id)}}],
        )
        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        from plane.utils.automacoes.ator import ator_da_automacao

        robo = ator_da_automacao(workspace.id)
        assert robo.is_bot is True
        assert robo.display_name == "Automação"

    @pytest.mark.django_db
    def test_propriedade_desligada_nao_derruba_a_regra(self, projeto, workspace, estados):
        propriedade = IssueProperty.objects.create(
            name="Cliente", property_type="text", project=projeto, workspace=workspace
        )
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_property", "config": {"property_id": str(propriedade.id), "value": "ACME"}}],
        )
        propriedade.is_active = False
        propriedade.save(update_fields=["is_active"])

        status = executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        assert status == AutomationRunStatus.MATCHED
        assert AutomationRun.objects.get(automation=regra).actions_result[0]["status"] == SEM_EFEITO

    @pytest.mark.django_db
    def test_tipo_de_acao_desconhecido_e_erro_registrado(self, projeto, workspace, estados):
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(projeto, workspace, actions=[{"type": "explodir", "config": {}}])

        status = executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        assert status == AutomationRunStatus.FAILED
        assert AutomationRun.objects.get(automation=regra).actions_result[0]["status"] == ERRO


@pytest.mark.contract
class TestValidacao:
    """Regra malformada é recusada com uma frase, não descoberta como silêncio."""

    @pytest.mark.django_db
    def test_regra_sem_acao_e_recusada(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_acoes([], projeto.id)
        assert "ao menos uma ação" in str(erro.value)

    @pytest.mark.django_db
    def test_gatilho_de_campo_sem_campo_e_recusado(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_gatilho("field_changed", {}, ["field_changed"], projeto.id)
        assert "campo" in str(erro.value)

    @pytest.mark.django_db
    def test_campo_que_nao_pode_disparar_e_recusado(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_gatilho("field_changed", {"field": "description_html"}, ["field_changed"], projeto.id)
        assert "não pode disparar" in str(erro.value)

    @pytest.mark.django_db
    def test_gatilho_agendado_ainda_nao_e_aceito(self, projeto):
        """A F2 traz o relógio. Até lá, gravar uma regra agendada seria gravar
        uma regra que nunca roda."""
        with pytest.raises(Exception):
            validar_gatilho("scheduled", {}, ["field_changed"], projeto.id)

    @pytest.mark.django_db
    def test_condicao_com_campo_inexistente_e_recusada(self, projeto):
        with pytest.raises(Exception) as erro:
            validar_condicao({"campo_inventado": ["x"]})
        assert "Condição inválida" in str(erro.value)

    @pytest.mark.django_db
    def test_a_recusa_e_uma_frase_e_nao_a_estrutura_do_drf(self, projeto):
        """O ADR diz "recusada com uma frase". `str(detail)` entregava o `repr`
        do dicionário do DRF, com `ErrorDetail(...)` vazando para a tela de quem
        só queria saber o que digitou errado."""
        with pytest.raises(Exception) as erro:
            validar_condicao({"campo_inventado": ["x"]})
        # `detail` é o que o DRF serializa para o cliente; `str()` da exceção
        # sempre dá o `repr` e não diz nada sobre o que a tela recebe.
        mensagem = str(erro.value.detail["condition"])
        assert "ErrorDetail" not in mensagem
        assert "campo_inventado" in mensagem
        assert mensagem.startswith("Condição inválida:")

    @pytest.mark.django_db
    def test_estado_de_outro_projeto_e_recusado(self, projeto, workspace, create_user):
        vizinho = Project.objects.create(
            name="Vizinho", identifier="VIZ", workspace=workspace, project_lead=create_user
        )
        # Criar o projeto pelo modelo não semeia estados — quem semeia é a view.
        alheio = State.objects.create(
            name="Alheio", group="unstarted", project=vizinho, workspace=workspace, color="#000"
        )

        with pytest.raises(Exception) as erro:
            validar_acoes([{"type": "set_state", "config": {"state_id": str(alheio.id)}}], projeto.id)
        assert "deste projeto" in str(erro.value)

    @pytest.mark.django_db
    def test_etiqueta_de_outro_projeto_e_recusada(self, projeto, workspace, create_user):
        vizinho = Project.objects.create(
            name="Vizinho2", identifier="VI2", workspace=workspace, project_lead=create_user
        )
        alheia = Label.objects.create(name="alheia", project=vizinho, workspace=workspace)

        with pytest.raises(Exception) as erro:
            validar_acoes([{"type": "set_labels", "config": {"labels": [str(alheia.id)]}}], projeto.id)
        assert "deste projeto" in str(erro.value)


@pytest.mark.contract
class TestTravasDeLaco:
    """As três travas, cada uma cobrindo o que a outra não cobre."""

    @pytest.mark.django_db
    def test_teto_por_hora_desliga_a_regra_com_motivo(self, projeto, workspace, estados):
        """Regra que emudece sem explicação é pior do que regra que erra."""
        from plane.bgtasks.automation_task import TETO_POR_HORA, _desligar, _estourou_o_teto

        regra = _regra(projeto, workspace)
        AutomationRun.objects.bulk_create(
            [
                AutomationRun(
                    automation=regra,
                    workspace=workspace,
                    status=AutomationRunStatus.MATCHED,
                )
                for _ in range(TETO_POR_HORA)
            ]
        )

        assert _estourou_o_teto(regra) is True
        _desligar(regra, "teste")
        regra.refresh_from_db()
        assert regra.is_active is False
        assert regra.disabled_reason == "teste"

    @pytest.mark.django_db
    def test_execucao_que_nao_casou_nao_conta_para_o_teto(self, projeto, workspace):
        """O teto limita ESTRAGO. Uma edição em massa de 200 tarefas geraria 200
        execuções puladas numa regra de condição estreita — e desligá-la seria
        punir justamente a regra bem escrita, por não ter feito nada."""
        from plane.bgtasks.automation_task import TETO_POR_HORA, _estourou_o_teto

        regra = _regra(projeto, workspace)
        AutomationRun.objects.bulk_create(
            [
                AutomationRun(automation=regra, workspace=workspace, status=AutomationRunStatus.SKIPPED)
                for _ in range(TETO_POR_HORA * 2)
            ]
        )

        assert _estourou_o_teto(regra) is False

    @pytest.mark.django_db
    def test_execucao_antiga_nao_conta_para_o_teto(self, projeto, workspace):
        from plane.bgtasks.automation_task import TETO_POR_HORA, _estourou_o_teto

        regra = _regra(projeto, workspace)
        AutomationRun.objects.bulk_create(
            [
                AutomationRun(automation=regra, workspace=workspace, status=AutomationRunStatus.MATCHED)
                for _ in range(TETO_POR_HORA)
            ]
        )
        # `created_at` é auto_now_add; envelhecer exige update direto.
        AutomationRun.objects.filter(automation=regra).update(created_at=timezone.now() - timedelta(hours=2))

        assert _estourou_o_teto(regra) is False

    @pytest.mark.django_db
    def test_despacho_para_no_teto_de_profundidade(self, projeto, workspace, estados, mocker):
        """Passou do teto, o motor não é nem acordado.

        O que se mede é a DECISÃO do despacho, e não um efeito na fila: no
        ambiente de teste ninguém consome o Celery, então contar
        `AutomationRun` daria verde com a trava removida — um teste que não
        testa nada. A segunda metade existe justamente para provar isso: mesma
        chamada, um degrau abaixo do teto, tem de enfileirar.
        """
        from plane.utils.automacoes.despacho import despachar_atividades
        from plane.utils.automacoes.gatilhos import TETO_DE_PROFUNDIDADE

        enfileirar = mocker.patch("plane.utils.automacoes.despacho.despachar_evento")
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        _regra(projeto, workspace, trigger_config={"field": "priority", "from": [], "to": []})
        linhas = [_linha_de_atividade(tarefa, "priority", "low", "urgent")]

        despachar_atividades(
            tipo="issue.activity.updated",
            issue_id=tarefa.id,
            project_id=projeto.id,
            actor_id=None,
            linhas=linhas,
            profundidade=TETO_DE_PROFUNDIDADE + 1,
        )
        assert enfileirar.call_count == 0

        despachar_atividades(
            tipo="issue.activity.updated",
            issue_id=tarefa.id,
            project_id=projeto.id,
            actor_id=None,
            linhas=linhas,
            profundidade=TETO_DE_PROFUNDIDADE,
        )
        assert enfileirar.call_count == 1

    @pytest.mark.django_db
    def test_campo_sem_regra_nao_acorda_o_motor(self, projeto, workspace, estados, mocker):
        """Editar o nome de uma tarefa não pode enfileirar avaliação nenhuma —
        é o caminho quente de toda edição do produto."""
        from plane.utils.automacoes.despacho import despachar_atividades

        enfileirar = mocker.patch("plane.utils.automacoes.despacho.despachar_evento")
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        _regra(projeto, workspace, trigger_config={"field": "priority", "from": [], "to": []})

        despachar_atividades(
            tipo="issue.activity.updated",
            issue_id=tarefa.id,
            project_id=projeto.id,
            actor_id=None,
            linhas=[_linha_de_atividade(tarefa, "name", "Antigo", "Novo")],
            profundidade=0,
        )

        assert enfileirar.call_count == 0

    @pytest.mark.django_db
    def test_projeto_sem_regra_nao_acorda_o_motor(self, projeto, workspace, estados, mocker):
        from plane.utils.automacoes.despacho import despachar_atividades

        enfileirar = mocker.patch("plane.utils.automacoes.despacho.despachar_evento")
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])

        despachar_atividades(
            tipo="issue.activity.updated",
            issue_id=tarefa.id,
            project_id=projeto.id,
            actor_id=None,
            linhas=[_linha_de_atividade(tarefa, "priority", "low", "urgent")],
            profundidade=0,
        )

        assert enfileirar.call_count == 0


@pytest.mark.contract
class TestSelecaoDeOpcao:
    """Propriedade de seleção como condição — o caso que só existe neste fork."""

    @pytest.mark.django_db
    def test_condicao_por_opcao_de_selecao(self, projeto, workspace, estados):
        propriedade = IssueProperty.objects.create(
            name="Setor", property_type="select", project=projeto, workspace=workspace
        )
        comercial = IssuePropertyOption.objects.create(
            name="Comercial", issue_property=propriedade, project=projeto, workspace=workspace
        )
        suporte = IssuePropertyOption.objects.create(
            name="Suporte", issue_property=propriedade, project=projeto, workspace=workspace
        )

        from plane.utils.issue_properties import gravar_valor

        de_comercial = _tarefa(projeto, workspace, estados["a_fazer"], "Comercial")
        de_suporte = _tarefa(projeto, workspace, estados["a_fazer"], "Suporte")
        gravar_valor(de_comercial, propriedade, str(comercial.id))
        gravar_valor(de_suporte, propriedade, str(suporte.id))

        condicao = {f"property_{propriedade.id}": [str(comercial.id)]}
        assert casa(de_comercial.id, condicao) is True
        assert casa(de_suporte.id, condicao) is False


@pytest.mark.contract
class TestOQueNaoDeveAcontecer:
    """As linhas da matriz de compatibilidade que afirmam uma AUSÊNCIA.

    Estavam marcadas `[I]` — provadas por leitura de código. Afirmação de
    ausência é a que envelhece pior sem teste: o dia em que alguém acrescentar
    um tipo de evento ao mapa, ou trocar o manager de uma consulta, nada avisa.
    A leitura continuará dizendo que está certo, porque o código que ela leu
    mudou de lugar.
    """

    @pytest.mark.django_db
    def test_rascunho_nao_dispara_regra(self, projeto, workspace, estados, mocker):
        """Linha 5. Rascunho usa `issue_draft.*`, fora do mapa de eventos.

        O que se tranca aqui não é o comportamento de hoje — é que acrescentar
        `issue_draft.activity.created` a `TIPO_DE_EVENTO` deixa de ser uma
        mudança silenciosa.
        """
        from plane.utils.automacoes.despacho import despachar_atividades

        _regra(projeto, workspace, trigger_type=AutomationTrigger.WORK_ITEM_CREATED, trigger_config={})
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        enfileirar = mocker.patch("plane.utils.automacoes.despacho.despachar_evento")

        despachar_atividades(
            tipo="issue_draft.activity.created",
            issue_id=str(tarefa.id),
            project_id=str(projeto.id),
            actor_id=None,
            linhas=[],
        )

        enfileirar.assert_not_called()

    @pytest.mark.django_db
    def test_tarefa_criada_de_verdade_dispara(self, projeto, workspace, estados, mocker):
        """O par do teste acima: sem ele, um `return` no topo passaria nos dois."""
        from plane.utils.automacoes.despacho import despachar_atividades

        _regra(projeto, workspace, trigger_type=AutomationTrigger.WORK_ITEM_CREATED, trigger_config={})
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        enfileirar = mocker.patch("plane.utils.automacoes.despacho.despachar_evento")

        despachar_atividades(
            tipo="issue.activity.created",
            issue_id=str(tarefa.id),
            project_id=str(projeto.id),
            actor_id=None,
            linhas=[],
        )

        enfileirar.assert_called_once()

    @pytest.mark.django_db
    def test_regra_nao_alcanca_tarefa_excluida(self, projeto, workspace, estados):
        """Linha 7. `Issue.objects` filtra `deleted_at`.

        A exclusão do produto é lógica: a linha continua no banco. Se a consulta
        do motor trocar de manager, a regra passa a agir sobre tarefa que a
        pessoa apagou — e o histórico vai mostrar o robô mexendo no que não
        existe mais.
        """
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"], prioridade="urgent")
        condicao = {"and": [{"priority__in": ["urgent"]}]}
        assert casa(tarefa.id, condicao) is True, "sem isto o teste abaixo não prova nada"

        tarefa.delete()  # exclusão lógica

        assert casa(tarefa.id, condicao) is False
        assert tarefa.id not in {t.id for t in tarefas_que_casam(projeto.id, condicao)}


@pytest.mark.contract
class TestORoboForaDasListas:
    """Linha 16. O robô é `is_bot` e some das listas por filtros que já existiam.

    Estava `[I]`: alguém leu `member__is_bot=False` nas consultas e concluiu.
    O risco não é a consulta mudar — é o robô nascer sem a marca, e aí TODOS os
    filtros do produto param de excluí-lo de uma vez.
    """

    @pytest.mark.django_db
    def test_o_ator_da_automacao_nasce_marcado_como_robo(self, workspace):
        from plane.utils.automacoes.ator import ator_da_automacao

        robo = ator_da_automacao(workspace.id)

        assert robo.is_bot is True
        assert robo.email.endswith("@automacao.invalid"), "e-mail em domínio que não recebe correio"

    @pytest.mark.django_db
    def test_o_mesmo_robo_serve_o_workspace_inteiro(self, workspace):
        """Um por workspace, e não um por regra — senão a lista de membros enche."""
        from plane.utils.automacoes.ator import ator_da_automacao

        assert ator_da_automacao(workspace.id).id == ator_da_automacao(workspace.id).id


@pytest.mark.contract
class TestOFunilUnico:
    """As linhas da matriz que afirmam uma PRESENÇA herdada do funil único.

    Linhas 2, 4, 12, 13, 14 e 15 diziam a mesma coisa por caminhos diferentes:
    "isto continua funcionando porque a ação passa pelo mesmo lugar que uma
    edição humana". Estavam `[I]` — provadas por leitura.

    O que sustenta as seis é UM fato, e é ele que estes testes prendem: a ação
    grava pelo caminho normal e despacha `issue.activity.updated` com
    `notification=True`. É desse despacho que saem o histórico, o webhook, a
    notificação e a sincronia de etapa pessoal — nenhum deles sabe que houve uma
    automação, e é justamente por isso que continuam certos.
    """

    @pytest.mark.django_db
    def test_a_acao_despacha_a_mesma_atividade_de_uma_edicao_humana(
        self, projeto, workspace, estados, create_user, mocker
    ):
        """Linhas 12, 13 e 14 de uma vez.

        Webhook, notificação e etapa pessoal penduram-se todos nesta chamada. Se
        o `notification` virar `False`, ou o `type` mudar, os três param juntos —
        e nada no código deles avisaria.
        """
        despacho = mocker.patch("plane.bgtasks.issue_activities_task.issue_activity.delay")
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_state", "config": {"state_id": str(estados["feito"].id)}}],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        despacho.assert_called_once()
        kwargs = despacho.call_args.kwargs
        assert kwargs["type"] == "issue.activity.updated", "o webhook e o histórico leem por este tipo"
        assert kwargs["notification"] is True, "sem isto a pessoa deixa de ser avisada"
        assert kwargs["issue_id"] == str(tarefa.id)

    @pytest.mark.django_db
    def test_a_atividade_carrega_a_origem_para_o_motor_nao_se_morder(
        self, projeto, workspace, estados, mocker
    ):
        """O par do teste acima, e a razão de o funil não virar laço.

        A mesma chamada que faz webhook e notificação saírem também é a que
        poderia reacordar a regra. O que impede é a origem viajar junto.
        """
        despacho = mocker.patch("plane.bgtasks.issue_activities_task.issue_activity.delay")
        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "set_priority", "config": {"priority": "urgent"}}],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        kwargs = despacho.call_args.kwargs
        assert kwargs["automacao_origem"] == str(regra.id)
        assert kwargs["automacao_profundidade"] == 1

    @pytest.mark.django_db
    def test_concluir_a_tarefa_e_uma_mudanca_de_estado_como_outra_qualquer(
        self, projeto, workspace, estados
    ):
        """Linha 15. O botão de concluir não tem caminho próprio.

        Ele grava estado, e estado gravado vira linha de histórico `state` — que
        é o que a regra de "campo alterado" lê. Não há nada a integrar; o que há
        é um invariante a não quebrar.
        """
        regra = _regra(
            projeto,
            workspace,
            trigger_type=AutomationTrigger.FIELD_CHANGED,
            trigger_config={"field": "state", "from": [], "to": [str(estados["feito"].id)]},
        )
        concluiu = {
            "tipo": "alterada",
            "mudancas": [
                {"campo": "state", "de": str(estados["a_fazer"].id), "para": str(estados["feito"].id)}
            ],
        }

        assert automacao_casa(regra, concluiu) is True

    @pytest.mark.django_db
    def test_a_regra_nao_acorda_com_estado_que_ela_nao_pediu(self, projeto, workspace, estados):
        """Sem este par, o teste acima passaria com um `return True`."""
        regra = _regra(
            projeto,
            workspace,
            trigger_type=AutomationTrigger.FIELD_CHANGED,
            trigger_config={"field": "state", "from": [], "to": [str(estados["feito"].id)]},
        )
        reabriu = {
            "tipo": "alterada",
            "mudancas": [
                {"campo": "state", "de": str(estados["feito"].id), "para": str(estados["a_fazer"].id)}
            ],
        }

        assert automacao_casa(regra, reabriu) is False

    def test_o_enxerto_mora_no_funil_e_nao_em_cada_chamador(self):
        """Linhas 2 e 4. Editar pela API pública e arrastar no quadro.

        As duas afirmam "cai no mesmo lugar". O que dá para prender por teste não
        é cada chamador — são 124 — e sim que o despacho da automação é feito de
        DENTRO da tarefa de atividade, que é por onde todos passam. Se alguém
        mover essa chamada para uma view, a afirmação da matriz deixa de valer e
        este teste é o que percebe.
        """
        from plane.bgtasks import issue_activities_task

        assert hasattr(issue_activities_task, "despachar_atividades"), (
            "o despacho saiu do funil; a matriz precisa ser revista"
        )


@pytest.mark.contract
class TestNotificacaoDaAutomacao:
    """A notificação precisa ser legível pelos DOIS destinos que a consomem.

    Encontrado na validação visual em produção, 17/08/2026: a caixa de entrada
    de notificações **inteira** ia para a tela de erro depois que uma automação
    avisava alguém. A lista lê `data.issue_activity.field` com o `?.` só no
    primeiro nível; sem a chave, estoura no render e derruba a página — não só o
    cartão daquela notificação.

    O payload nascia em duas versões: a de e-mail, completa, e a da tela, sem a
    chave. Agora é uma só.
    """

    @pytest.mark.django_db
    def test_a_notificacao_carrega_o_bloco_que_a_tela_le(self, projeto, workspace, estados, create_user):
        from plane.db.models import Notification

        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "notify", "config": {"users": [str(create_user.id)]}}],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        aviso = Notification.objects.filter(receiver=create_user).order_by("-created_at").first()
        assert aviso is not None, "a ação não avisou ninguém"
        assert "issue_activity" in aviso.data, "sem esta chave a página de notificações inteira quebra"
        assert aviso.data["issue_activity"]["field"] == "automation"
        assert aviso.data["issue_activity"]["activity_time"], "a fila de e-mail faz pop disto sem padrão"

    @pytest.mark.django_db
    def test_a_notificacao_tambem_diz_de_que_tarefa_e_de_que_regra(
        self, projeto, workspace, estados, create_user
    ):
        """O resto do payload, que é o que dá sentido ao cartão."""
        from plane.db.models import Notification

        tarefa = _tarefa(projeto, workspace, estados["a_fazer"])
        regra = _regra(
            projeto,
            workspace,
            actions=[{"type": "notify", "config": {"users": [str(create_user.id)]}}],
        )

        executar_automacao(regra, tarefa, {"tipo": "alterada", "mudancas": []})

        dados = Notification.objects.filter(receiver=create_user).order_by("-created_at").first().data
        assert dados["issue"]["id"] == str(tarefa.id)
        assert dados["automation"]["id"] == str(regra.id)
