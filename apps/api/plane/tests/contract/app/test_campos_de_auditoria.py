# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`created_by` e `updated_by` nunca vêm do cliente.

Defeito da revisão do upstream (branch `secur-236`): com `fields = "__all__"` —
o que a maioria dos serializers usa — os campos de auditoria entram como
escrevíveis. E o `BaseModel.save()` só mexe em `created_by` na **criação**; numa
atualização ele toca apenas em `updated_by`. Então um `PATCH` com `created_by`
de outra pessoa passava pelo serializer e ninguém o sobrescrevia depois.

Medido antes da correção: `PATCH /projects/<id>/` com
`{"created_by": "<outro usuário>"}` respondeu 200 e o banco passou a atribuir o
projeto a quem nunca o criou.

O aviso do upstream explicava a falha por outro caminho — dizia que `save()` só
preenche `created_by` quando está `None`, "então um valor enviado sobreviveria".
No **nosso** `save()` isso é falso na criação: ele sobrescreve com o usuário do
pedido. O vetor aqui é o `PATCH`, não o `POST`, e foi medir que mostrou a
diferença.

A correção mora em `get_fields` das duas classes base, e não nos 52 serializers
que têm a lacuna: `read_only_fields` do `Meta` **não se herda** — cada subclasse
declara o seu do zero, então a regra escrita lá se perde na próxima classe que
alguém criar.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.api.serializers.base import BaseSerializer as BaseSerializerPublica
from plane.app.serializers.base import BaseSerializer as BaseSerializerApp
from plane.db.models import Project, ProjectMember, User, WorkspaceMember


@pytest.fixture
def projeto(db, workspace, create_user):
    p = Project.objects.create(name="Auditoria", identifier="AUD", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=p, member=create_user, workspace=workspace, role=20)
    return p


@pytest.fixture
def outra_pessoa(db, workspace):
    marca = uuid4().hex[:8]
    u = User.objects.create(email=f"outra-{marca}@plane.so", username=f"outra_{marca}")
    u.set_password("test-password")
    u.save()
    WorkspaceMember.objects.create(workspace=workspace, member=u, role=15)
    return u


@pytest.mark.contract
class TestForjarAutoria:
    @pytest.mark.django_db
    def test_patch_nao_reescreve_quem_criou_o_projeto(self, db, workspace, create_user, projeto, outra_pessoa):
        cliente = APIClient()
        cliente.force_authenticate(user=create_user)
        # Guardado ANTES, e não comparado com `create_user`: fora de um pedido,
        # o `save()` grava `created_by = None`, então a fixture não decide esse
        # valor. O que se afirma é que o PATCH não o mudou.
        autoria_antes = Project.objects.values_list("created_by_id", flat=True).get(pk=projeto.id)

        resposta = cliente.patch(
            f"/api/workspaces/{workspace.slug}/projects/{projeto.id}/",
            {"created_by": str(outra_pessoa.id), "description": "mudei a descrição"},
            format="json",
        )

        # A recusa é silenciosa, e é o comportamento certo: campo somente-leitura
        # no DRF é ignorado, não motivo de erro. O pedido legítimo passa.
        assert resposta.status_code == status.HTTP_200_OK, resposta.data
        projeto.refresh_from_db()
        assert projeto.description == "mudei a descrição", "o campo legítimo tinha de ter sido aplicado"
        assert projeto.created_by_id != outra_pessoa.id, "a autoria foi reescrita pelo cliente"
        assert projeto.created_by_id == autoria_antes, "a autoria mudou, mesmo sem ser para o valor forjado"

    @pytest.mark.django_db
    def test_patch_nao_reescreve_quem_atualizou(self, db, workspace, create_user, projeto, outra_pessoa):
        """`updated_by` estava contido por sorte, não por regra.

        O `save()` o sobrescreve em toda atualização, então o valor do cliente
        já morria ali. Este teste tranca a regra em vez da sorte: se alguém
        mudar o `save()`, quebra aqui.
        """
        cliente = APIClient()
        cliente.force_authenticate(user=create_user)

        cliente.patch(
            f"/api/workspaces/{workspace.slug}/projects/{projeto.id}/",
            {"updated_by": str(outra_pessoa.id), "description": "x"},
            format="json",
        )

        projeto.refresh_from_db()
        assert projeto.updated_by_id == create_user.id


@pytest.mark.contract
class TestARegraValeParaTodaSubclasse:
    """A prova de que a correção não é uma lista de exceções.

    Um serializer novo, escrito hoje ou amanhã, herda a regra sem que ninguém
    precise lembrar de declará-la — que é a única razão de a correção estar na
    classe base e não nos 52 serializers que tinham a lacuna.
    """

    @pytest.mark.parametrize("base", [BaseSerializerApp, BaseSerializerPublica])
    @pytest.mark.django_db
    def test_serializer_novo_ja_nasce_com_auditoria_travada(self, base):
        class SerializerRecemNascido(base):
            class Meta:
                model = Project
                fields = "__all__"

        campos = SerializerRecemNascido().get_fields()
        assert campos["created_by"].read_only is True
        assert campos["updated_by"].read_only is True

    @pytest.mark.parametrize("base", [BaseSerializerApp, BaseSerializerPublica])
    @pytest.mark.django_db
    def test_as_datas_ja_estavam_travadas_por_outro_motivo(self, base):
        """E é por isso que elas NÃO entraram na nossa lista.

        Escrevi a lista supondo que `created_at`/`updated_at` ficariam de fora
        por escolha, para não atrapalhar importação que preserva data original.
        Medindo, a suposição caiu: `auto_now_add`/`auto_now` tornam o campo não
        editável no modelo, e o DRF já o marca somente-leitura sozinho.

        Acrescentá-los à `CAMPOS_DE_AUDITORIA` seria código que não faz nada.
        Este teste guarda o motivo, para a próxima pessoa não achar que faltou.
        """

        class SerializerRecemNascido(base):
            class Meta:
                model = Project
                fields = "__all__"

        campos = SerializerRecemNascido().get_fields()
        assert campos["created_at"].read_only is True
        assert campos["updated_at"].read_only is True
