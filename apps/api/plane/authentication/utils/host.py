# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpRequest

# Third party imports
from rest_framework.request import Request

# Module imports
from plane.utils.ip_address import get_client_ip


def _origem_do_pedido(request) -> str | None:
    """A origem de QUEM chamou, quando ela é reconhecidamente nossa.

    Evolury: existe para o ambiente de desenvolvimento, onde a mesma instância
    é aberta por vários nomes — `localhost`, o IP da rede e o nome do tailnet.
    O redirecionamento pós-login é montado pelo servidor a partir de um
    endereço FIXO, então entrar por um nome e ser jogado noutro é o
    comportamento padrão — e de outra máquina isso leva a um host que ela não
    alcança.

    Só age quando `TRUST_REQUEST_ORIGIN` está ligada, e mesmo assim só aceita
    origem que já está na lista de CORS. Sem a variável — que é o caso de
    produção — esta função não faz nada, e o comportamento é o de sempre.

    A lista fechada é o ponto: redirecionar para uma origem arbitrária vinda do
    pedido é a receita de redirecionamento aberto, e não é isso que se faz aqui.
    """
    if not getattr(settings, "TRUST_REQUEST_ORIGIN", False):
        return None
    origem = request.META.get("HTTP_ORIGIN") or None
    if not origem:
        referer = request.META.get("HTTP_REFERER")
        if referer:
            partes = urlparse(referer)
            origem = f"{partes.scheme}://{partes.netloc}" if partes.netloc else None
    if not origem:
        return None
    permitidas = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []) or [])
    return origem if origem in permitidas else None


def base_host(
    request: Request | HttpRequest,
    is_admin: bool = False,
    is_space: bool = False,
    is_app: bool = False,
) -> str:
    """Utility function to return host / origin from the request"""
    # Calculate the base origin from request
    base_origin = _origem_do_pedido(request) or settings.WEB_URL or settings.APP_BASE_URL

    # Admin redirection
    if is_admin:
        admin_base_path = getattr(settings, "ADMIN_BASE_PATH", None)
        if not isinstance(admin_base_path, str):
            admin_base_path = "/god-mode/"
        if not admin_base_path.startswith("/"):
            admin_base_path = "/" + admin_base_path
        if not admin_base_path.endswith("/"):
            admin_base_path += "/"

        if settings.ADMIN_BASE_URL:
            return settings.ADMIN_BASE_URL + admin_base_path
        else:
            return base_origin + admin_base_path

    # Space redirection
    if is_space:
        space_base_path = getattr(settings, "SPACE_BASE_PATH", None)
        if not isinstance(space_base_path, str):
            space_base_path = "/spaces/"
        if not space_base_path.startswith("/"):
            space_base_path = "/" + space_base_path
        if not space_base_path.endswith("/"):
            space_base_path += "/"

        if settings.SPACE_BASE_URL:
            return settings.SPACE_BASE_URL + space_base_path
        else:
            return base_origin + space_base_path

    # App Redirection
    if is_app:
        # Evolury: a origem do pedido, quando confiável, ganha do endereço fixo
        if _origem_do_pedido(request):
            return base_origin
        if settings.APP_BASE_URL:
            return settings.APP_BASE_URL
        else:
            return base_origin

    return base_origin


def user_ip(request: Request | HttpRequest) -> str:
    return get_client_ip(request=request)
