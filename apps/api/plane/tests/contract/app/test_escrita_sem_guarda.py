# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Nenhuma rota de escrita da app API pode cair no CRUD genérico do DRF.

O defeito que originou este arquivo (revisão do upstream, SECUR-248): os
arquivos de URL mapeavam ``"put": "update"`` em treze lugares, e **nenhum**
viewset da app API define ``update``. O verbo caía no ``UpdateModelMixin`` do
DRF, que não sabe nada de papéis, sob o único ``permission_classes`` da
``BaseViewSet`` — ``IsAuthenticated``. Resultado medido antes da correção:
qualquer pessoa autenticada, membro do workspace mas de fora do projeto,
renomeava módulo e tarefa de projeto alheio com um PUT.

O aviso do upstream citava só o PUT de projeto. A varredura mostrou dezoito
pares (rota, ação) com a mesma forma e seis exploráveis de verdade. Corrigir só
o citado seria deixar cinco buracos conhecidos abertos.

São dois testes com propósitos diferentes, e os dois precisam existir:

* :func:`test_nenhuma_rota_de_escrita_cai_no_crud_do_drf` é estrutural. Falha no
  instante em que alguém acrescentar um mapeamento novo sem escrever o handler
  — inclusive numa rota que este arquivo nunca imaginou.
* :class:`TestDeForaNaoEscreve` é comportamental. Prova que a recusa acontece de
  fato, com requisição de verdade, e não só que a fiação parece certa.
"""

from uuid import uuid4

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIClient

from plane.db.models import (
    Cycle,
    Intake,
    Issue,
    IssueView,
    Module,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

METODOS_SEGUROS = {"get", "head", "options"}

#: As classes de onde vem o CRUD que ninguém escreveu.
BASES_DO_DRF = (
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ModelViewSet,
    viewsets.GenericViewSet,
)


def _percorrer(patterns, prefixo=""):
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from _percorrer(p.url_patterns, prefixo + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield prefixo + str(p.pattern), p.callback


def _classe_que_define(cls, nome):
    for base in cls.__mro__:
        if nome in base.__dict__:
            return base
    return None


@pytest.mark.contract
def test_nenhuma_rota_de_escrita_cai_no_crud_do_drf():
    """Toda ação de escrita alcançável tem dono: ou handler próprio, ou guarda.

    Uma ação é aceita quando alguma destas é verdade:

    * o viewset a escreve e decora com ``allow_permission`` (o ``functools.wraps``
      do decorador deixa o ``__wrapped__`` como marca);
    * o viewset declara um ``permission_classes`` mais estrito que o padrão.

    Se nenhuma for, o que responde ao verbo é o mixin do DRF sob
    ``IsAuthenticated`` — e isso é o defeito, não uma escolha.
    """
    sem_dono = []
    for rota, callback in _percorrer(get_resolver("plane.app.urls").url_patterns):
        acoes = getattr(callback, "actions", None)
        cls = getattr(callback, "cls", None)
        if not acoes or cls is None:
            continue
        for metodo, acao in acoes.items():
            if metodo in METODOS_SEGUROS:
                continue
            func = getattr(cls, acao, None)
            if func is None:
                continue
            veio_do_drf = _classe_que_define(cls, acao) in BASES_DO_DRF
            tem_decorador = hasattr(func, "__wrapped__")
            so_autenticado = [c.__name__ for c in (cls.permission_classes or [])] == [IsAuthenticated.__name__]
            if veio_do_drf and so_autenticado and not tem_decorador:
                sem_dono.append(f"{metodo.upper()} /{rota} -> {cls.__name__}.{acao}")

    assert sem_dono == [], "rotas de escrita sem guarda:\n  " + "\n  ".join(sorted(sem_dono))


@pytest.fixture
def cenario(db, workspace, create_user):
    """Um projeto com conteúdo, e alguém de fora dele para bater na porta.

    O de fora é membro do workspace e membro de OUTRO projeto de propósito: sem
    isso, a recusa poderia vir de "não é membro de nada", que não é o que se
    quer provar. O que se prova é o recorte por projeto.
    """
    projeto = Project.objects.create(name="Alvo", identifier="ALV", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=projeto, member=create_user, workspace=workspace, role=20)

    estado = State.objects.create(name="A fazer", project=projeto, workspace=workspace, group="unstarted")
    tarefa = Issue.objects.create(name="Tarefa", project=projeto, workspace=workspace, state=estado)
    modulo = Module.objects.create(name="Módulo", project=projeto, workspace=workspace)
    ciclo = Cycle.objects.create(name="Ciclo", project=projeto, workspace=workspace, owned_by=create_user)
    visao = IssueView.objects.create(name="Visão", project=projeto, workspace=workspace, query={}, owned_by=create_user)
    visao_workspace = IssueView.objects.create(name="Visão WS", workspace=workspace, query={}, owned_by=create_user)
    caixa = Intake.objects.create(name="Entrada", project=projeto, workspace=workspace)

    marca = uuid4().hex[:8]
    de_fora = User.objects.create(email=f"defora-{marca}@plane.so", username=f"defora_{marca}")
    de_fora.set_password("test-password")
    de_fora.save()
    WorkspaceMember.objects.create(workspace=workspace, member=de_fora, role=15)
    outro = Project.objects.create(name="Outro", identifier="OUT", workspace=workspace, created_by=de_fora)
    ProjectMember.objects.create(project=outro, member=de_fora, workspace=workspace, role=15)

    cliente = APIClient()
    cliente.force_authenticate(user=de_fora)
    return {
        "cliente": cliente,
        "slug": workspace.slug,
        "projeto": projeto,
        "tarefa": tarefa,
        "modulo": modulo,
        "ciclo": ciclo,
        "visao": visao,
        "visao_workspace": visao_workspace,
        "caixa": caixa,
    }


@pytest.mark.contract
class TestDeForaNaoEscreve:
    """Cada método aqui reproduz uma escrita que passava e hoje não passa."""

    @pytest.mark.django_db
    def test_put_nao_existe_mais_em_lugar_nenhum(self, cenario):
        """PUT some com 405: não havia handler, havia rota para o mixin.

        405 e não 403 de propósito — a defesa é a ausência da rota, que não
        depende de ninguém lembrar de decorar nada.
        """
        s, c = cenario["slug"], cenario["cliente"]
        p = cenario["projeto"].id
        alvos = [
            f"/api/workspaces/{s}/projects/{p}/",
            f"/api/workspaces/{s}/projects/{p}/issues/{cenario['tarefa'].id}/",
            f"/api/workspaces/{s}/projects/{p}/modules/{cenario['modulo'].id}/",
            f"/api/workspaces/{s}/projects/{p}/cycles/{cenario['ciclo'].id}/",
            f"/api/workspaces/{s}/projects/{p}/views/{cenario['visao'].id}/",
            f"/api/workspaces/{s}/views/{cenario['visao_workspace'].id}/",
        ]
        for url in alvos:
            resposta = c.put(url, {"name": "INVADIDO"}, format="json")
            assert resposta.status_code == 405, f"{url} respondeu {resposta.status_code}"

    @pytest.mark.django_db
    def test_tarefa_e_modulo_alheios_continuam_com_o_nome_deles(self, cenario):
        """A prova que interessa: o dado não mudou.

        Status de recusa é a promessa; o nome no banco é o cumprimento.
        """
        s, c = cenario["slug"], cenario["cliente"]
        p = cenario["projeto"].id
        c.put(f"/api/workspaces/{s}/projects/{p}/issues/{cenario['tarefa'].id}/", {"name": "INVADIDO"}, format="json")
        c.put(f"/api/workspaces/{s}/projects/{p}/modules/{cenario['modulo'].id}/", {"name": "INVADIDO"}, format="json")

        cenario["tarefa"].refresh_from_db()
        cenario["modulo"].refresh_from_db()
        assert cenario["tarefa"].name == "Tarefa"
        assert cenario["modulo"].name == "Módulo"

    @pytest.mark.django_db
    def test_de_fora_nao_cria_visao_no_projeto_alheio(self, cenario):
        s, c = cenario["slug"], cenario["cliente"]
        resposta = c.post(
            f"/api/workspaces/{s}/projects/{cenario['projeto'].id}/views/",
            {"name": "Minha visão", "query": {}},
            format="json",
        )
        assert resposta.status_code == 403

    @pytest.mark.django_db
    def test_convidado_do_workspace_nao_cria_visao_de_workspace(self, db, workspace):
        """O POST de visão de workspace aceitava qualquer autenticado.

        Agora vale a mesma régua do resto do produto: convidado não cria.
        """
        marca = uuid4().hex[:8]
        convidado = User.objects.create(email=f"conv-{marca}@plane.so", username=f"conv_{marca}")
        convidado.set_password("test-password")
        convidado.save()
        WorkspaceMember.objects.create(workspace=workspace, member=convidado, role=5)
        cliente = APIClient()
        cliente.force_authenticate(user=convidado)

        resposta = cliente.post(
            f"/api/workspaces/{workspace.slug}/views/", {"name": "Visão", "query": {}}, format="json"
        )
        assert resposta.status_code == 403
        assert not IssueView.objects.filter(name="Visão", project__isnull=True).exists()

    @pytest.mark.django_db
    def test_de_fora_nao_edita_a_caixa_de_entrada_alheia(self, cenario):
        s, c = cenario["slug"], cenario["cliente"]
        resposta = c.patch(
            f"/api/workspaces/{s}/projects/{cenario['projeto'].id}/intakes/{cenario['caixa'].id}/",
            {"name": "MUDADO"},
            format="json",
        )
        assert resposta.status_code == 403
        cenario["caixa"].refresh_from_db()
        assert cenario["caixa"].name == "Entrada"

    @pytest.mark.django_db
    def test_criar_caixa_de_entrada_responde_recusa_e_nao_erro(self, cenario):
        """O POST estourava 500: o decorador estava no ``perform_create``.

        Um 500 esconde a resposta certa — e esconde também que a rota nunca foi
        exercitada. Hoje responde 403, que é uma decisão.
        """
        s, c = cenario["slug"], cenario["cliente"]
        resposta = c.post(
            f"/api/workspaces/{s}/projects/{cenario['projeto'].id}/intakes/", {"name": "Nova"}, format="json"
        )
        assert resposta.status_code == 403

    @pytest.mark.django_db
    def test_membro_do_projeto_continua_criando_caixa_de_entrada(self, db, workspace, create_user):
        """A outra metade: o guarda não pode ter fechado a porta de quem pode.

        Sem este teste, um `return 403` chapado passaria em todos os de cima.
        """
        projeto = Project.objects.create(name="Meu", identifier="MEU", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=projeto, member=create_user, workspace=workspace, role=20)
        cliente = APIClient()
        cliente.force_authenticate(user=create_user)

        resposta = cliente.post(
            f"/api/workspaces/{workspace.slug}/projects/{projeto.id}/intakes/", {"name": "Nova"}, format="json"
        )
        assert resposta.status_code == 201, resposta.data
        assert Intake.objects.filter(project=projeto, name="Nova").exists()
