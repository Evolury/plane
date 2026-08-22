# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Recusa por plano — ver ADR 0021.

**402, e não 403.** Papel é permissão: "você não pode". Plano é dinheiro: "isto
não está no seu plano". São recusas diferentes e levam a telas diferentes —
uma pede outro usuário, a outra vende. Misturá-las obrigaria o cliente a
adivinhar qual é qual pelo texto da mensagem.

A resposta diz **onde está** o que a pessoa quis: recusar sem apontar o caminho
transforma a trava em parede, e parede não vende plano nenhum.
"""

from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

from plane.utils import direitos


class ForaDoPlano(APIException):
    status_code = 402
    default_detail = "Este recurso não está no plano deste espaço de trabalho."


def ExigePlanoCom(recurso: str, exige_espaco: bool = True):
    """Fábrica de permissão: `permission_classes = [..., ExigePlanoCom("analytics")]`.

    Lê `view.workspace_slug` sem rede de proteção **por padrão**: view sem
    espaço no caminho não tem plano a consultar, e responder "pode" em silêncio
    nesse caso seria o buraco que esta classe existe para fechar. Melhor quebrar
    no primeiro teste do que liberar em produção.

    `exige_espaco=False` é a exceção medida, e existe por um caso real: a API
    pública tem rotas de identidade (`/api/v1/users/me/`) que não pertencem a
    espaço nenhum. Recusá-las por plano diria a quem tem token válido que ele
    não pode nem saber quem é — e a primeira execução da suíte mostrou isso
    exatamente assim, com 500.
    """

    class ExigePlano(BasePermission):
        def has_permission(self, request, view):
            slug = view.workspace_slug
            if slug is None and not exige_espaco:
                return True
            if direitos.recurso_liberado(recurso, slug=slug):
                return True
            raise ForaDoPlano(direitos.recusa_de_recurso(recurso, direitos.plano_de(slug=slug)))

    ExigePlano.__name__ = f"ExigePlanoCom_{recurso}"
    return ExigePlano
