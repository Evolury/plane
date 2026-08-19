# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Uma tarefa tem um responsável, e nunca mais de um (ADR 0016).

A garantia que interessa é a do **banco**: o índice único parcial em
`issue_assignees(issue_id)` faz dois responsáveis serem impossíveis, valha o
pedido pela tela, pela API, por importação ou por SQL direto. A normalização nas
portas de escrita existe para que essa rede não precise ser usada — mas é a rede
que define a promessa, e é ela que este arquivo prende primeiro.

A segunda afirmação é a regra de desempate: quando chegam dois, **fica o
último**. É escolha do produto, e se implementa ao contrário com a mesma
facilidade — trocar `[-1:]` por `[:1]` não quebra nada que não seja um teste.
"""

import pytest
from django.db import IntegrityError, transaction

from plane.db.models import Issue, IssueAssignee, Project, ProjectMember, User, WorkspaceMember
from plane.utils.responsavel import apenas_um, excedentes


@pytest.fixture
def projeto(db, workspace, create_user):
    p = Project.objects.create(name="Responsável", identifier="RSP", workspace=workspace)
    ProjectMember.objects.create(project=p, member=create_user, workspace=workspace, role=20)
    return p


@pytest.fixture
def outra_pessoa(db, workspace, projeto):
    pessoa = User.objects.create(email="outra@evolury.test", username="outra-resp")
    pessoa.set_password("senha-de-teste")
    pessoa.save()
    WorkspaceMember.objects.create(workspace=workspace, member=pessoa, role=20)
    ProjectMember.objects.create(project=projeto, member=pessoa, workspace=workspace, role=20)
    return pessoa


@pytest.fixture
def tarefa(db, projeto, workspace, create_user):
    return Issue.objects.create(name="Tarefa", project=projeto, workspace=workspace, created_by=create_user)


def url_tarefas(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/issues/"


@pytest.mark.django_db
class TestOBancoRecusa:
    def test_dois_responsaveis_na_mesma_tarefa_nao_entram(
        self, tarefa, projeto, workspace, create_user, outra_pessoa
    ):
        IssueAssignee.objects.create(
            issue=tarefa, assignee=create_user, project=projeto, workspace=workspace
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                IssueAssignee.objects.create(
                    issue=tarefa, assignee=outra_pessoa, project=projeto, workspace=workspace
                )

    def test_a_mesma_pessoa_em_tarefas_diferentes_continua_valendo(
        self, projeto, workspace, create_user
    ):
        uma = Issue.objects.create(name="A", project=projeto, workspace=workspace, created_by=create_user)
        outra = Issue.objects.create(name="B", project=projeto, workspace=workspace, created_by=create_user)

        for alvo in (uma, outra):
            IssueAssignee.objects.create(
                issue=alvo, assignee=create_user, project=projeto, workspace=workspace
            )

        assert IssueAssignee.objects.filter(assignee=create_user).count() == 2

    def test_trocar_de_responsavel_continua_possivel(
        self, tarefa, projeto, workspace, create_user, outra_pessoa
    ):
        antiga = IssueAssignee.objects.create(
            issue=tarefa, assignee=create_user, project=projeto, workspace=workspace
        )
        # A troca apaga por soft delete e insere: a linha antiga sai do índice
        # parcial, então a nova entra.
        antiga.delete()
        IssueAssignee.objects.create(
            issue=tarefa, assignee=outra_pessoa, project=projeto, workspace=workspace
        )

        ativos = IssueAssignee.objects.filter(issue=tarefa, deleted_at__isnull=True)
        assert [v.assignee_id for v in ativos] == [outra_pessoa.id]


@pytest.mark.django_db
class TestFicaOUltimo:
    def test_a_normalizacao_guarda_o_ultimo(self):
        assert apenas_um(["a", "b", "c"]) == ["c"]

    def test_lista_vazia_esvazia_e_none_nao_mexe(self):
        # A diferença importa: `[]` é "tirei o responsável", `None` é "não toquei".
        assert apenas_um([]) == []
        assert apenas_um(None) is None

    def test_pela_api_enviar_dois_grava_o_ultimo(
        self, session_client, workspace, projeto, create_user, outra_pessoa
    ):
        resposta = session_client.post(
            url_tarefas(workspace.slug, projeto.id),
            {"name": "Com dois", "assignee_ids": [str(create_user.id), str(outra_pessoa.id)]},
            format="json",
        )

        assert resposta.status_code == 201
        tarefa_id = resposta.data["id"]
        ativos = IssueAssignee.objects.filter(issue_id=tarefa_id, deleted_at__isnull=True)
        assert [v.assignee_id for v in ativos] == [outra_pessoa.id]

    def test_a_resposta_devolve_o_responsavel_efetivo(
        self, session_client, workspace, projeto, create_user, outra_pessoa
    ):
        # É o que permite a quem integra perceber que mandou dois e ficou um.
        resposta = session_client.post(
            url_tarefas(workspace.slug, projeto.id),
            {"name": "Com dois", "assignee_ids": [str(create_user.id), str(outra_pessoa.id)]},
            format="json",
        )

        assert [str(x) for x in resposta.data["assignee_ids"]] == [str(outra_pessoa.id)]

    def test_trocar_pela_api_substitui_e_nao_acumula(
        self, session_client, workspace, projeto, create_user, outra_pessoa
    ):
        criada = session_client.post(
            url_tarefas(workspace.slug, projeto.id),
            {"name": "Troca", "assignee_ids": [str(create_user.id)]},
            format="json",
        )
        alvo = f"{url_tarefas(workspace.slug, projeto.id)}{criada.data['id']}/"

        session_client.patch(alvo, {"assignee_ids": [str(outra_pessoa.id)]}, format="json")

        ativos = IssueAssignee.objects.filter(issue_id=criada.data["id"], deleted_at__isnull=True)
        assert [v.assignee_id for v in ativos] == [outra_pessoa.id]


@pytest.mark.django_db
class TestSemResponsavelContinuaValido:
    def test_criar_sem_ninguem(self, session_client, workspace, projeto):
        resposta = session_client.post(
            url_tarefas(workspace.slug, projeto.id), {"name": "Sem dono"}, format="json"
        )

        assert resposta.status_code == 201
        assert IssueAssignee.objects.filter(issue_id=resposta.data["id"]).count() == 0

    def test_esvaziar_tira_o_responsavel(
        self, session_client, workspace, projeto, create_user
    ):
        criada = session_client.post(
            url_tarefas(workspace.slug, projeto.id),
            {"name": "Some", "assignee_ids": [str(create_user.id)]},
            format="json",
        )
        alvo = f"{url_tarefas(workspace.slug, projeto.id)}{criada.data['id']}/"

        session_client.patch(alvo, {"assignee_ids": []}, format="json")

        assert (
            IssueAssignee.objects.filter(
                issue_id=criada.data["id"], deleted_at__isnull=True
            ).count()
            == 0
        )


class TestOColapsoDaMigracao:
    """A suíte roda com `--nomigrations` e nunca executa a migração.

    Por isso a regra de quem sobrevive foi extraída para `excedentes()`: sem
    isso, a decisão que o banco de produção vai aplicar uma única vez ficaria
    sem nenhum teste.
    """

    def test_sobrevive_o_mais_recente_de_cada_tarefa(self):
        linhas = [
            ("v1", "tarefa-a", 1),
            ("v2", "tarefa-a", 3),
            ("v3", "tarefa-a", 2),
            ("v4", "tarefa-b", 9),
        ]

        assert sorted(excedentes(linhas)) == ["v1", "v3"]

    def test_empate_no_instante_desempata_pelo_id_e_nao_pelo_acaso(self):
        # Sem o desempate, duas execuções escolheriam sobreviventes diferentes,
        # e a migração deixaria de ser determinística.
        linhas = [("aaa", "tarefa", 5), ("zzz", "tarefa", 5)]

        assert excedentes(linhas) == ["aaa"]
        assert excedentes(list(reversed(linhas))) == ["aaa"]

    def test_quem_ja_tem_um_so_nao_perde_ninguem(self):
        assert excedentes([("v1", "tarefa-a", 1), ("v2", "tarefa-b", 1)]) == []
