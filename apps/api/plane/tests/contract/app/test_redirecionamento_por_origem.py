# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O redirecionamento pós-login pode seguir a origem — só no desenvolvimento.

A instância de desenvolvimento é aberta por vários nomes: `localhost`, o IP da
rede e o nome do tailnet. O endereço do redirecionamento é montado pelo
servidor a partir de uma configuração FIXA, então entrar por um nome e ser
jogado noutro é o padrão — e de outra máquina isso leva a um host inalcançável.

O que estes testes protegem é o CONTRÁRIO: que nada disso valha sem a chave
ligada, e que origem fora da lista nunca seja seguida. Redirecionar para o que
o pedido mandar é a receita de redirecionamento aberto.
"""

import pytest
from django.test import RequestFactory, override_settings

from plane.authentication.utils.host import base_host

FIXO = "https://fixo.example.com"
CONHECIDA = "http://worklab.tail6ece57.ts.net:3000"
DESCONHECIDA = "https://invasor.example.com"


def _pedido(origem=None, referer=None):
    req = RequestFactory().get("/auth/sign-in/")
    if origem:
        req.META["HTTP_ORIGIN"] = origem
    if referer:
        req.META["HTTP_REFERER"] = referer
    return req


@pytest.mark.contract
class TestRedirecionamentoPorOrigem:
    @override_settings(TRUST_REQUEST_ORIGIN=False, WEB_URL=FIXO, APP_BASE_URL=FIXO, CORS_ALLOWED_ORIGINS=[CONHECIDA])
    def test_desligada_ignora_a_origem(self):
        """É o caso de produção: o endereço é um e fixo."""
        assert base_host(_pedido(origem=CONHECIDA), is_app=True) == FIXO

    @override_settings(TRUST_REQUEST_ORIGIN=True, WEB_URL=FIXO, APP_BASE_URL=FIXO, CORS_ALLOWED_ORIGINS=[CONHECIDA])
    def test_ligada_segue_a_origem_conhecida(self):
        assert base_host(_pedido(origem=CONHECIDA), is_app=True) == CONHECIDA

    @override_settings(TRUST_REQUEST_ORIGIN=True, WEB_URL=FIXO, APP_BASE_URL=FIXO, CORS_ALLOWED_ORIGINS=[CONHECIDA])
    def test_origem_fora_da_lista_nunca_e_seguida(self):
        """O ponto do recorte: sem lista fechada, isto seria redirecionamento aberto."""
        assert base_host(_pedido(origem=DESCONHECIDA), is_app=True) == FIXO

    @override_settings(TRUST_REQUEST_ORIGIN=True, WEB_URL=FIXO, APP_BASE_URL=FIXO, CORS_ALLOWED_ORIGINS=[CONHECIDA])
    def test_referer_vale_quando_nao_ha_origem(self):
        """Navegação direta manda `Referer` e não `Origin`."""
        assert base_host(_pedido(referer=f"{CONHECIDA}/evolury/"), is_app=True) == CONHECIDA

    @override_settings(TRUST_REQUEST_ORIGIN=True, WEB_URL=FIXO, APP_BASE_URL=FIXO, CORS_ALLOWED_ORIGINS=[CONHECIDA])
    def test_referer_de_fora_da_lista_e_ignorado(self):
        assert base_host(_pedido(referer=f"{DESCONHECIDA}/qualquer/"), is_app=True) == FIXO

    @override_settings(TRUST_REQUEST_ORIGIN=True, WEB_URL=FIXO, APP_BASE_URL=FIXO, CORS_ALLOWED_ORIGINS=[CONHECIDA])
    def test_sem_cabecalho_nenhum_usa_o_fixo(self):
        assert base_host(_pedido(), is_app=True) == FIXO
