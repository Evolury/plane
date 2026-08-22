# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O painel de assinaturas do god-mode — ver ADR 0021.

Existe para que operar o faturamento não seja `psql`. Três coisas moram aqui, e
cada uma resolve um caso real:

- **Ver**: quem está em qual plano, em qual estado, e quão perto do teto. É a
  planilha que a operação teria de manter à mão.
- **Bloquear e liberar**: o Asaas não bloqueia nada por nós. Quando o financeiro
  processa um estorno, ou quando um cliente precisa ser cortado por outro
  motivo, é aqui — sem depender de webhook nenhum.
- **Conceder plano e cortesia**: o comercial classifica os espaços em cortesia
  de transição antes de o prazo acabar.

**Todo ato administrativo grava histórico com autor e motivo.** É a mesma regra
dos ADRs 0010 e 0011: o ato não é bloqueado, e a consequência dele nunca é
silenciosa. Aqui vale duas vezes, porque cada linha destas mexe em dinheiro.
"""

from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, F, Func, OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.bgtasks.faturamento_conciliacao import CHAVE_DO_ALARME, CHAVE_DO_ULTIMO_EVENTO
from plane.db.models import Assinatura, HistoricoDeAssinatura, WorkspaceMember
from plane.license.api.permissions import InstanceAdminPermission
from plane.utils import planos, regua

ACAO_BLOQUEAR = "bloquear"
ACAO_LIBERAR = "liberar"
ACAO_PLANO = "atribuir_plano"
ACAO_CORTESIA = "conceder_cortesia"
ACOES = (ACAO_BLOQUEAR, ACAO_LIBERAR, ACAO_PLANO, ACAO_CORTESIA)


def _contagem(**filtros):
    """Subconsulta de contagem — é o que evita uma consulta por linha."""
    return Subquery(
        WorkspaceMember.objects.filter(
            workspace_id=OuterRef("workspace_id"), is_active=True, member__is_bot=False, **filtros
        )
        .order_by()
        .annotate(total=Func(F("id"), function="Count"))
        .values("total")
    )


class InstanceAssinaturasEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        assinaturas = Assinatura.objects.select_related("workspace").annotate(
            membros=_contagem(role__in=[20, 15]),
            convidados=_contagem(role=5),
        )

        estado = request.query_params.get("status")
        if estado:
            assinaturas = assinaturas.filter(status=estado)

        busca = request.query_params.get("search")
        if busca:
            assinaturas = assinaturas.filter(Q(workspace__name__icontains=busca) | Q(workspace__slug__icontains=busca))

        so_excedentes = request.query_params.get("excedentes") == "1"

        return self.paginate(
            request=request,
            queryset=assinaturas.order_by("workspace__name"),
            on_results=lambda resultados: [
                linha for linha in (self._linha(a) for a in resultados) if not so_excedentes or linha["excedente"] > 0
            ],
            max_per_page=25,
            default_per_page=25,
        )

    def _linha(self, assinatura):
        membros = assinatura.membros or 0
        pagos = assinatura.assentos_incluidos + assinatura.assentos_extras
        return {
            "id": str(assinatura.id),
            "workspace_id": str(assinatura.workspace_id),
            "nome": assinatura.workspace.name,
            "slug": assinatura.workspace.slug,
            "plano": assinatura.plano,
            "ciclo": assinatura.ciclo,
            "status": assinatura.status,
            "pago_ate": assinatura.pago_ate,
            "proxima_cobranca_em": assinatura.proxima_cobranca_em,
            "promocao_termina_em": assinatura.promocao_termina_em,
            "remover_dados_em": assinatura.remover_dados_em,
            "assentos_incluidos": assinatura.assentos_incluidos,
            "assentos_extras": assinatura.assentos_extras,
            "membros": membros,
            # Excedente é o que passou dos assentos pagos. Zero quando cabe.
            "excedente": max(membros - pagos, 0),
            "convidados": assinatura.convidados or 0,
            "convidados_cota": assinatura.convidados_por_assento * pagos,
            "valor": assinatura.valor_base + assinatura.valor_por_assento * assinatura.assentos_extras,
            "asaas_subscription_id": assinatura.asaas_subscription_id,
        }


class InstanceSaudeDoFaturamentoEndpoint(BaseAPIView):
    """Quando o último evento chegou, e se o alarme está aceso.

    Fila interrompida é silenciosa: o Asaas para depois de 15 falhas seguidas e
    ninguém avisa. Este é o lugar onde alguém vê.
    """

    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        contagens = dict(
            Assinatura.objects.values_list("status").annotate(total=Count("id")).order_by()
        )
        return Response(
            {
                "ultimo_evento_em": cache.get(CHAVE_DO_ULTIMO_EVENTO),
                "alarme": cache.get(CHAVE_DO_ALARME),
                "por_status": {estado: contagens.get(estado, 0) for estado in regua.ESTADOS},
                "planos": list(planos.CHAVES),
                "estados": list(regua.ESTADOS),
            },
            status=status.HTTP_200_OK,
        )


class InstanceAssinaturaEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    def get(self, request, workspace_id):
        historico = HistoricoDeAssinatura.objects.filter(assinatura__workspace_id=workspace_id).select_related(
            "created_by"
        )[:100]
        return Response(
            [
                {
                    "id": str(linha.id),
                    "evento": linha.evento,
                    "de": linha.de,
                    "para": linha.para,
                    "motivo": linha.motivo,
                    "quando": linha.created_at,
                    "quem": getattr(linha.created_by, "display_name", "") or "sistema",
                }
                for linha in historico
            ],
            status=status.HTTP_200_OK,
        )

    def patch(self, request, workspace_id):
        assinatura = Assinatura.objects.filter(workspace_id=workspace_id).first()
        if assinatura is None:
            return Response({"error": "SEM_ASSINATURA"}, status=status.HTTP_404_NOT_FOUND)

        acao = request.data.get("acao")
        if acao not in ACOES:
            return Response({"error": "ACAO_INVALIDA", "acoes": list(ACOES)}, status=status.HTTP_400_BAD_REQUEST)

        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            # Sem motivo o histórico vira uma lista de mudanças sem explicação,
            # que é o mesmo que não ter histórico.
            return Response({"error": "MOTIVO_OBRIGATORIO"}, status=status.HTTP_400_BAD_REQUEST)

        de = assinatura.status
        hoje = timezone.now().date()

        if acao == ACAO_BLOQUEAR:
            assinatura.status = regua.BLOQUEADA
        elif acao == ACAO_LIBERAR:
            # Volta para o que a régua disser: liberar não perdoa dívida, só
            # desfaz o bloqueio manual.
            assinatura.status = regua.estado_de_hoje(
                estado=regua.ATIVA, pago_ate=assinatura.pago_ate, hoje=hoje
            )
        elif acao == ACAO_PLANO:
            chave = request.data.get("plano")
            if not planos.existe(chave):
                return Response(
                    {"error": "PLANO_INVALIDO", "planos": list(planos.CHAVES)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ciclo = request.data.get("ciclo") or assinatura.ciclo or planos.CICLO_MENSAL
            for campo, valor in planos.copia_para_contrato(chave, ciclo).items():
                setattr(assinatura, campo, valor)
        elif acao == ACAO_CORTESIA:
            dias = int(request.data.get("dias") or 0)
            if dias <= 0:
                return Response({"error": "DIAS_INVALIDOS"}, status=status.HTTP_400_BAD_REQUEST)
            chave = request.data.get("plano") or assinatura.plano or planos.AVANCADO
            for campo, valor in planos.copia_para_contrato(
                chave, assinatura.ciclo or planos.CICLO_MENSAL, gratuita=True
            ).items():
                setattr(assinatura, campo, valor)
            assinatura.status = regua.EM_CORTESIA
            # Cortesia sem data é assinatura grátis para sempre, em silêncio.
            assinatura.pago_ate = hoje + timedelta(days=dias)
            assinatura.promocao_termina_em = assinatura.pago_ate

        assinatura.save()

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento=f"god_mode:{acao}",
            de=de,
            para=assinatura.status,
            motivo=motivo[:500],
            # O autor vem do `CurrentRequestUserMiddleware`, que o `save()` do
            # `BaseModel` já consulta. Passá-lo à mão aqui era uma segunda fonte
            # para o mesmo dado — e a injeção mostrou: remover a linha não
            # mudava nada, porque o middleware preenchia igual. Histórico
            # criado por tarefa continua sem autor, que é o certo: quem agiu
            # foi o sistema.
        )

        return Response({"status": assinatura.status, "plano": assinatura.plano}, status=status.HTTP_200_OK)
