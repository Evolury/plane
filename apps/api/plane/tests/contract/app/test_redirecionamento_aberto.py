# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O redirecionamento pós-autenticação nunca sai do nosso host.

Escrito na triagem de seis alertas `py/url-redirection` (médio) que o CodeQL
abriu em 17/08/2026, nas telas de entrada e cadastro do app e do space. Eles
apareceram porque a limitação de tentativas de senha tocou aqueles arquivos e
forçou uma reanálise — os achados já estavam lá, sem ninguém ver.

**Os seis são falsos positivos, e este arquivo é o motivo escrito.** O CodeQL vê
`request.POST["next_path"]` chegar a `HttpResponseRedirect` e não reconhece
`validate_next_path` como sanitizador. O que ele não segue:

* `next_path` é reduzido a CAMINHO RELATIVO — esquema e host são descartados,
  e o que não começar com `/` vira vazio;
* a BASE do redirecionamento não vem do pedido. Ela é uma configuração fixa,
  salvo quando `TRUST_REQUEST_ORIGIN` está ligada — e aí só aceita origem que já
  está na lista fechada de CORS. Produção não liga a variável.

Dispensar um alerta de segurança é uma afirmação sobre o futuro, e ela não pode
depender de alguém reler duas funções daqui a seis meses. Por isso a dispensa
vem acompanhada destes testes: se o sanitizador enfraquecer, quebram aqui.
"""

import pytest

from plane.utils.path_validator import get_safe_redirect_url, validate_next_path

NOSSA_BASE = "https://plane.example.com"


@pytest.fixture
def nosso_host(settings):
    """Põe `NOSSA_BASE` na lista de hosts permitidos.

    Sem isto, `get_safe_redirect_url` cai na terceira camada — a conferência da
    URL final — e devolve só a base, o que faria os testes passarem pelo motivo
    errado: nada teria sido saneado, apenas descartado.
    """
    settings.WEB_URL = NOSSA_BASE
    settings.APP_BASE_URL = NOSSA_BASE
    return NOSSA_BASE

#: Cada carga é uma forma conhecida de escapar de um redirecionamento relativo.
CARGAS_HOSTIS = [
    pytest.param("https://attacker.example/roubado", id="url-absoluta"),
    pytest.param("//attacker.example/roubado", id="barra-dupla"),
    pytest.param("\\\\attacker.example/roubado", id="barra-invertida-dupla"),
    pytest.param("/\\attacker.example", id="barra-e-invertida"),
    pytest.param("https:attacker.example", id="esquema-sem-barras"),
    pytest.param("javascript:alert(1)", id="javascript"),
    pytest.param("data:text/html,<script>alert(1)</script>", id="data-url"),
    pytest.param("vbscript:msgbox(1)", id="vbscript"),
    pytest.param("file:///etc/passwd", id="file"),
    pytest.param("/..//attacker.example", id="travessia"),
    pytest.param("%2f%2fattacker.example", id="barra-dupla-codificada"),
    pytest.param("/legitimo/../../attacker.example", id="travessia-no-meio"),
    pytest.param("/@attacker.example", id="arroba"),
    pytest.param("http://attacker.example\t/x", id="tabulacao"),
    pytest.param("x" * 501, id="longa-demais"),
]


@pytest.mark.contract
class TestONextPathNaoLevaParaFora:
    @pytest.mark.parametrize("carga", CARGAS_HOSTIS)
    def test_carga_hostil_e_descartada_ou_vira_caminho_relativo(self, carga):
        resultado = validate_next_path(carga)

        # Duas saídas aceitáveis, e nenhuma outra: descartar, ou reduzir a um
        # caminho que começa com uma barra só. `//x` é rejeitado de propósito —
        # o navegador o leria como host.
        assert resultado == "" or (resultado.startswith("/") and not resultado.startswith("//"))

    @pytest.mark.parametrize("carga", CARGAS_HOSTIS)
    def test_a_url_montada_continua_no_nosso_host(self, carga, nosso_host):
        """A afirmação que importa de fato: onde o navegador vai parar.

        Testar só o validador provaria que ele limpa a entrada, e não que a URL
        final é nossa — que é o que o alerta questiona.
        """
        from urllib.parse import urlparse

        url = get_safe_redirect_url(base_url=NOSSA_BASE, next_path=carga, params={"error_code": "X"})

        assert urlparse(url).netloc == urlparse(NOSSA_BASE).netloc

    def test_caminho_legitimo_sobrevive(self):
        """Sem isto, um sanitizador que devolvesse sempre vazio passaria em tudo acima."""
        assert validate_next_path("/evolury/projects/123/issues/") == "/evolury/projects/123/issues/"

    def test_caminho_legitimo_chega_na_url_final(self, nosso_host):
        url = get_safe_redirect_url(base_url=NOSSA_BASE, next_path="/evolury/inbox/", params={})

        assert url.startswith(NOSSA_BASE)
        assert "next_path=/evolury/inbox/" in url


@pytest.mark.contract
class TestATerceiraCamada:
    """A rede embaixo das outras duas, descoberta ao escrever este arquivo.

    Depois de sanear o caminho e montar a URL, `get_safe_redirect_url` ainda
    confere o resultado contra os hosts configurados e, não passando, devolve só
    a base. Foi ela que apareceu quando um teste montou a URL com uma base
    arbitrária: o `next_path` legítimo sumiu — não por defeito, mas porque a
    base não estava na lista.

    Vale trancar: é o que segura o caso em que alguém, um dia, enfraquecer o
    validador lá em cima.
    """

    def test_base_fora_da_lista_perde_o_next_path(self, settings):
        settings.WEB_URL = "https://plane.example.com"
        settings.APP_BASE_URL = ""
        settings.ADMIN_BASE_URL = ""
        settings.SPACE_BASE_URL = ""

        url = get_safe_redirect_url(base_url="https://outra.example", next_path="/evolury/inbox/", params={})

        assert "next_path" not in url


@pytest.mark.contract
class TestABaseNaoVemDoPedido:
    """A segunda entrada do redirecionamento, que o alerta não menciona.

    `base_host` só olha a origem de quem chamou quando `TRUST_REQUEST_ORIGIN`
    está ligada, e mesmo aí só aceita origem já presente na lista de CORS.
    Produção não liga a variável — mas a trava tem de ser a lista, e não o
    esquecimento de ligá-la.
    """

    def test_origem_de_terceiro_e_recusada_mesmo_com_a_variavel_ligada(self, settings):
        from plane.authentication.utils.host import _origem_do_pedido

        settings.TRUST_REQUEST_ORIGIN = True
        settings.CORS_ALLOWED_ORIGINS = ["https://plane.example.com"]

        class Pedido:
            META = {"HTTP_ORIGIN": "https://attacker.example"}

        assert _origem_do_pedido(Pedido()) is None

    def test_origem_conhecida_passa(self, settings):
        """Sem isto, recusar tudo passaria no teste acima — e o motivo de a
        função existir (abrir o dev por vários nomes) morreria em silêncio."""
        from plane.authentication.utils.host import _origem_do_pedido

        settings.TRUST_REQUEST_ORIGIN = True
        settings.CORS_ALLOWED_ORIGINS = ["https://plane.example.com"]

        class Pedido:
            META = {"HTTP_ORIGIN": "https://plane.example.com"}

        assert _origem_do_pedido(Pedido()) == "https://plane.example.com"

    def test_sem_a_variavel_a_origem_do_pedido_e_ignorada(self, settings):
        from plane.authentication.utils.host import _origem_do_pedido

        settings.TRUST_REQUEST_ORIGIN = False
        settings.CORS_ALLOWED_ORIGINS = ["https://plane.example.com"]

        class Pedido:
            META = {"HTTP_ORIGIN": "https://plane.example.com"}

        assert _origem_do_pedido(Pedido()) is None
