# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A cor de capa é `#RRGGBB`, e é o servidor quem cobra.

O valor vai do banco direto para um `style` do navegador. "Começa com #" seria
suficiente para desenhar e insuficiente para proteger: `#fff);background-image:
url(…` também começa com #, e o navegador leria o resto como mais CSS.

O front tem a mesma regra, e é por isso que estes testes existem — o front é
sugestão, e qualquer cliente pode falar com a API sem passar por ele.
"""

import pytest
from rest_framework import serializers

from plane.app.serializers.project import ProjectSerializer
from plane.app.serializers.user import UserSerializer
from plane.utils.cores import normalizar_cor_de_capa


@pytest.mark.unit
class TestNormalizarCorDeCapa:
    def test_aceita_a_forma_completa(self):
        assert normalizar_cor_de_capa("#0C91EB") == "#0C91EB"

    def test_normaliza_para_maiusculas(self):
        """Senão `#0c91eb` e `#0C91EB` viveriam como cores diferentes no banco,
        e "esta é a cor selecionada" deixaria de reconhecer a própria escolha."""
        assert normalizar_cor_de_capa("#0c91eb") == "#0C91EB"

    def test_vazio_e_ausencia_significam_sem_cor(self):
        assert normalizar_cor_de_capa(None) is None
        assert normalizar_cor_de_capa("") is None
        assert normalizar_cor_de_capa("   ") is None

    @pytest.mark.parametrize(
        "valor",
        [
            "#fff",  # forma curta: um formato só é um formato que não se adivinha
            "red",
            "rgb(12, 145, 235)",
            "#0C91EBB",
            "0C91EB",
            "#GGGGGG",
            123,
            ["#0C91EB"],
        ],
    )
    def test_recusa_o_que_nao_e_cor(self, valor):
        with pytest.raises(ValueError):
            normalizar_cor_de_capa(valor)

    @pytest.mark.parametrize(
        "ataque",
        [
            "#fff);background-image:url(https://exemplo.invalido/x.png",
            "#fff;behavior:url(#default#time2)",
            "#000</style><script>alert(1)</script>",
        ],
    )
    def test_recusa_css_disfarcado_de_cor(self, ataque):
        with pytest.raises(ValueError):
            normalizar_cor_de_capa(ataque)


@pytest.mark.unit
class TestValidacaoNosSerializers:
    """A regra tem de estar nos DOIS caminhos de escrita: projeto e perfil."""

    @pytest.mark.parametrize("serializer", [ProjectSerializer, UserSerializer])
    def test_aceita_cor_valida(self, serializer):
        assert serializer().validate_cover_color("#0c91eb") == "#0C91EB"

    @pytest.mark.parametrize("serializer", [ProjectSerializer, UserSerializer])
    def test_recusa_texto_livre(self, serializer):
        with pytest.raises(serializers.ValidationError):
            serializer().validate_cover_color("#fff);background:url(x)")
