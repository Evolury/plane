# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: endpoints das propriedades personalizadas (ADR 0011, P1).
#
# Escrever é porta de admin: criar propriedade cria trabalho para os outros —
# todo mundo passa a ver o campo, e a obrigatória passa a barrar criação. Ler é
# de todos, porque preencher valor é de quem pode editar a tarefa.

# Python imports
from collections import defaultdict

# Django imports
from django.db.models import Count

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.issue_property import IssuePropertySerializer
from plane.app.views.base import BaseViewSet
from plane.utils.edicao_em_massa import TETO_DE_EDICAO_EM_MASSA
from plane.utils.automacoes.despacho import registrar_atividade_de_propriedade
from plane.utils.issue_properties import (
    ValorInvalido,
    gravar_valor,
    rotulo_do_valor,
    validar_valores,
    valores_por_tarefa,
)
from plane.db.models import (
    Issue,
    IssueProperty,
    IssuePropertyOption,
    IssuePropertyValue,
    TIPOS_DE_SELECAO,
)
from plane.utils import direitos
from plane.utils.planos import LIMITE_PROPRIEDADES


class IssuePropertyViewSet(BaseViewSet):
    serializer_class = IssuePropertySerializer
    model = IssueProperty

    def get_queryset(self):
        return (
            IssueProperty.objects.filter(
                workspace__slug=self.kwargs.get("slug"), project_id=self.kwargs.get("project_id")
            )
            .prefetch_related("options")
            # `created_at` é o desempate: sem ele, duas propriedades com a
            # mesma ordem voltam em ordem indefinida do banco, e a lista muda
            # de posição entre um carregamento e outro.
            .order_by("sort_order", "created_at")
        )

    def _contagem_de_valores(self, propriedades):
        """Quantas TAREFAS usam cada propriedade, numa consulta só.

        Tarefas, e não linhas: seleção múltipla grava uma linha por opção, e
        dizer "12 valores serão perdidos" onde são 4 tarefas assustaria com um
        número que não é o da pergunta.

        O filtro de `deleted_at` na tarefa é explícito porque a junção não passa
        pelo manager de exclusão lógica — armadilha que já mordeu esta base.
        """
        contagens = defaultdict(int)
        linhas = (
            IssuePropertyValue.objects.filter(issue_property__in=propriedades, issue__deleted_at__isnull=True)
            .values("issue_property_id")
            .annotate(total=Count("issue_id", distinct=True))
        )
        for linha in linhas:
            contagens[linha["issue_property_id"]] = linha["total"]
        return contagens

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def list(self, request, slug, project_id):
        propriedades = list(self.get_queryset())
        serializer = IssuePropertySerializer(
            propriedades,
            many=True,
            context={"valores_por_propriedade": self._contagem_de_valores(propriedades)},
        )
        return Response(
            {"properties": serializer.data, "cap": self._teto(slug)},
            status=status.HTTP_200_OK,
        )

    # Evolury: o teto passa a vir do plano (ADR 0021). Era 30 para todo mundo;
    # agora é 5 no Essencial e 30 nos outros dois. Quem cai de plano acima do
    # teto **não perde** propriedade: para de criar. Apagar dado por mudança de
    # contrato seria cobrar o cliente duas vezes pela mesma decisão.
    def _teto(self, slug):
        # `None` é sem teto, e é diferente de zero, que é 'nenhuma'.
        return direitos.limite(LIMITE_PROPRIEDADES, slug=slug)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def create(self, request, slug, project_id):
        # O teto conta as ativas e as desativadas: desativar preserva os
        # valores, então a linha continua existindo e continua custando.
        teto = self._teto(slug)
        existentes = self.get_queryset().count()
        if teto is not None and existentes >= teto:
            return Response(
                direitos.recusa_de_limite(LIMITE_PROPRIEDADES, teto, direitos.plano_de(slug=slug)),
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        serializer = IssuePropertySerializer(data=request.data, context={"project_id": project_id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # O workspace vem do projeto pelo `save()` do `ProjectBaseModel` — é a
        # única fonte, e passá-lo à mão abriria caminho para divergir dela.
        #
        # A ordem nasce no fim da lista. Deixar todas no mesmo padrão faria o
        # banco devolver ordem indefinida, e a tela mudaria de arrumação a cada
        # carregamento sem ninguém ter mexido em nada.
        propriedade = serializer.save(project_id=project_id, sort_order=(existentes + 1) * 1000)
        self._gravar_opcoes(propriedade, request.data.get("options"))
        propriedade.refresh_from_db()
        return Response(IssuePropertySerializer(propriedade).data, status=status.HTTP_201_CREATED)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def partial_update(self, request, slug, project_id, pk):
        propriedade = self.get_queryset().filter(pk=pk).first()
        if propriedade is None:
            return Response({"error": "Propriedade não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        serializer = IssuePropertySerializer(
            propriedade, data=request.data, partial=True, context={"project_id": project_id}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        propriedade = serializer.save()
        if "options" in request.data:
            self._gravar_opcoes(propriedade, request.data.get("options"))
        propriedade.refresh_from_db()
        return Response(IssuePropertySerializer(propriedade).data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def destroy(self, request, slug, project_id, pk):
        propriedade = self.get_queryset().filter(pk=pk).first()
        if propriedade is None:
            return Response({"error": "Propriedade não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        # Os valores vão junto, pela cascata. A tela avisa quantas tarefas
        # perdem o preenchimento ANTES de chegar aqui — bloquear criaria o
        # incentivo perverso de sempre, que é apagar o que atrapalha.
        propriedade.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def reorder(self, request, slug, project_id):
        """A ordem em que os campos aparecem no cartão e na tabela."""
        ordem = request.data.get("order") or []
        conhecidas = {str(pk) for pk in self.get_queryset().values_list("id", flat=True)}
        for posicao, propriedade_id in enumerate(ordem):
            if str(propriedade_id) in conhecidas:
                IssueProperty.objects.filter(pk=propriedade_id).update(sort_order=(posicao + 1) * 1000)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def delete_option(self, request, slug, project_id, pk, option_id):
        """Exclui uma opção, mesmo em uso.

        A resposta devolve quantas tarefas ficaram sem valor — o ato não é
        bloqueado, e a consequência dele não é silenciosa (ADR 0011).
        """
        opcao = IssuePropertyOption.objects.filter(pk=option_id, issue_property_id=pk).first()
        if opcao is None or not self.get_queryset().filter(pk=pk).exists():
            return Response({"error": "Opção não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        afetadas = (
            IssuePropertyValue.objects.filter(value_option=opcao, issue__deleted_at__isnull=True)
            .values("issue_id")
            .distinct()
            .count()
        )
        opcao.delete()
        return Response({"cleared_work_items": afetadas}, status=status.HTTP_200_OK)

    def _gravar_opcoes(self, propriedade, opcoes):
        """Cria, renomeia e remove as opções de uma propriedade de seleção.

        Renomear vale para as tarefas que já usam a opção — o vínculo é por id,
        e é por isso que renomear não perde nada.
        """
        if propriedade.property_type not in TIPOS_DE_SELECAO or opcoes is None:
            return

        existentes = {str(o.id): o for o in propriedade.options.all()}
        vistas = set()
        for posicao, opcao in enumerate(opcoes):
            identificador = str(opcao.get("id") or "")
            campos = {
                "name": (opcao.get("name") or "").strip(),
                "color": opcao.get("color") or "",
                "sort_order": (posicao + 1) * 1000,
            }
            if not campos["name"]:
                continue
            if identificador in existentes:
                IssuePropertyOption.objects.filter(pk=identificador).update(**campos)
                vistas.add(identificador)
            else:
                nova = IssuePropertyOption.objects.create(
                    issue_property=propriedade,
                    project_id=propriedade.project_id,
                    workspace_id=propriedade.workspace_id,
                    **campos,
                )
                vistas.add(str(nova.id))

        # O que sumiu da lista foi removido na tela. Os valores vão junto pela
        # cascata; a contagem do que se perde é mostrada antes de salvar.
        for identificador, opcao in existentes.items():
            if identificador not in vistas:
                opcao.delete()


class IssuePropertyValuesBulkViewSet(BaseViewSet):
    """Os valores de uma PÁGINA de tarefas, numa consulta.

    Endpoint próprio, e não campo na listagem de tarefas: a listagem é o
    caminho quente do produto, com paginação, agrupamento e teto de consultas
    fixado em teste. É a mesma escolha que o selo do quadro fez na F6.5 da
    recorrência — uma pergunta enxuta, respondida de uma vez.
    """

    model = IssueProperty

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def list(self, request, slug, project_id):
        # Dois modos, e o segundo existe porque o cartão não conhece a página
        # em que está: `card_only` devolve o projeto inteiro, limitado às
        # propriedades marcadas para o cartão — uma marca que é opt-in.
        if request.GET.get("card_only"):
            do_cartao = list(
                IssueProperty.objects.filter(
                    project_id=project_id, is_active=True, show_on_card=True
                ).values_list("id", flat=True)
            )
            if not do_cartao:
                return Response({"values": {}}, status=status.HTTP_200_OK)
            ids = list(
                IssuePropertyValue.objects.filter(
                    issue_property_id__in=do_cartao, issue__deleted_at__isnull=True
                )
                .values_list("issue_id", flat=True)
                .distinct()
            )
            recorte = do_cartao
        else:
            ids = [i for i in (request.GET.get("issues") or "").split(",") if i]
            recorte = None
        if not ids:
            return Response({"values": {}}, status=status.HTTP_200_OK)
        valores = valores_por_tarefa(ids, property_ids=recorte)
        return Response(
            {"values": {str(tarefa): campos for tarefa, campos in valores.items()}},
            status=status.HTTP_200_OK,
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def create(self, request, slug, project_id):
        """Evolury: grava o MESMO valor em várias tarefas de uma vez (ADR 0019).

        É o "preencher a coluna" que a planilha faz e o produto não fazia:
        escolher trinta tarefas e dizer que o Canal de todas é Indicação.

        Escreve tarefa a tarefa de propósito. `gravar_valor` valida por tipo,
        converte e apaga com vazio, e `registrar_atividade_de_propriedade`
        escreve o histórico e acorda as automações (ADR 0012) — reproduzir isso
        em bloco criaria um segundo caminho para o mesmo destino, e é assim que
        os dois passam a divergir.
        """
        issue_ids = request.data.get("issue_ids", [])
        propriedade_id = request.data.get("property")
        novo_valor = request.data.get("value")

        if not len(issue_ids):
            return Response({"error": "ISSUE_IDS_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        if len(issue_ids) > TETO_DE_EDICAO_EM_MASSA:
            return Response(
                {"error": "TOO_MANY_ISSUES", "limit": TETO_DE_EDICAO_EM_MASSA},
                status=status.HTTP_400_BAD_REQUEST,
            )

        propriedade = IssueProperty.objects.filter(
            pk=propriedade_id, project_id=project_id, is_active=True
        ).first()
        if propriedade is None:
            return Response(
                {"property": "Propriedade não encontrada neste projeto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tarefas = list(Issue.objects.filter(pk__in=issue_ids, project_id=project_id))
        if not tarefas:
            return Response({"error": "ISSUES_NOT_FOUND"}, status=status.HTTP_400_BAD_REQUEST)

        # O valor é conferido UMA vez, contra a definição, antes de escrever em
        # trinta tarefas — recusar na décima deixaria nove preenchidas e vinte
        # e uma não, que é o pior desfecho possível.
        try:
            validar_valores(project_id, {str(propriedade.id): novo_valor})
        except ValorInvalido as erro:
            return Response({"value": str(erro)}, status=status.HTTP_400_BAD_REQUEST)

        anteriores = valores_por_tarefa([t.id for t in tarefas], property_ids=[propriedade.id])
        for tarefa in tarefas:
            anterior = anteriores.get(tarefa.id, {}).get(str(propriedade.id))
            gravar_valor(tarefa, propriedade, novo_valor)
            registrar_atividade_de_propriedade(
                tarefa=tarefa,
                propriedade=propriedade,
                de=rotulo_do_valor(propriedade, anterior),
                para=rotulo_do_valor(propriedade, novo_valor),
                actor_id=request.user.id,
            )

        return Response({"updated": len(tarefas)}, status=status.HTTP_200_OK)


class IssuePropertyOptionUsageViewSet(BaseViewSet):
    """Quantas tarefas usam uma opção — o número que a confirmação mostra."""

    model = IssuePropertyOption

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def retrieve(self, request, slug, project_id, pk, option_id):
        opcao = IssuePropertyOption.objects.filter(pk=option_id, issue_property_id=pk, project_id=project_id).first()
        if opcao is None:
            return Response({"error": "Opção não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        total = (
            IssuePropertyValue.objects.filter(value_option=opcao, issue__deleted_at__isnull=True)
            .values("issue_id")
            .distinct()
            .count()
        )
        return Response({"work_items": total}, status=status.HTTP_200_OK)
