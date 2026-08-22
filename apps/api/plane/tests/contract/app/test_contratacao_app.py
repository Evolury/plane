# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contratar, trocar de plano e ver o histórico (ADR 0021).

O Asaas é substituído **na única função de transporte**, e é por isso que estes
testes conseguem conferir o que seria enviado a ele: o corpo é montado pelo
cliente de verdade, com o valor em reais, o ciclo traduzido e o
`externalReference` com o prefixo que separa o nosso do que é dos outros
negócios da conta.

Nenhuma chamada sai desta máquina — e agora isso é obrigação, não higiene: a
chave da instância é de produção.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Cobranca, Cupom, HistoricoDeAssinatura, ProjectMember, Project, State
from plane.utils import cupons, regua
from plane.utils.planos import AVANCADO, CICLO_MENSAL, ESSENCIAL, PROFISSIONAL, copia_para_contrato

DADOS_URL = "/api/workspaces/{slug}/faturamento/dados-de-cobranca/"
CUPOM_URL = "/api/workspaces/{slug}/faturamento/cupom/"
CONTRATAR_URL = "/api/workspaces/{slug}/faturamento/contratar/"
TROCAR_URL = "/api/workspaces/{slug}/faturamento/trocar-plano/"
COBRANCAS_URL = "/api/workspaces/{slug}/faturamento/cobrancas/"

CPF = "111.444.777-35"


@pytest.fixture
def session_client(create_user):
    cliente = APIClient()
    cliente.force_authenticate(user=create_user)
    return cliente


@pytest.fixture
def enviado(mocker):
    """Guarda o que teria ido para o Asaas, e devolve respostas plausíveis."""
    chamadas = []

    def falso(metodo, caminho, corpo=None, parametros=None):
        chamadas.append({"metodo": metodo, "caminho": caminho, "corpo": corpo, "parametros": parametros})
        if caminho == "customers":
            return {"id": "cus_001"}
        if caminho == "subscriptions":
            return {"id": "sub_001", "nextDueDate": "2026-09-21"}
        if caminho.startswith("subscriptions/"):
            return {"id": "sub_001"}
        if caminho == "checkouts":
            return {"id": "chk_001", "link": "https://asaas.com/checkout/chk_001"}
        if caminho == "payments" and metodo == "POST":
            return {"id": "pay_extra", "invoiceUrl": "https://asaas.com/i/pay_extra", "value": 200.0}
        if caminho == "payments":
            return {"data": [{"id": "pay_001", "invoiceUrl": "https://asaas.com/i/pay_001"}]}
        return {}

    mocker.patch("plane.utils.asaas._requisitar", side_effect=falso)
    mocker.patch(
        "plane.utils.asaas.configuracao",
        return_value={"chave": "chave-de-teste", "ambiente": "producao", "token_do_webhook": "t"},
    )
    return chamadas


@pytest.fixture
def com_dados(db, workspace):
    assinatura = workspace.assinatura
    assinatura.nome_de_cobranca = "Evolury LTDA"
    assinatura.cpf_cnpj = "11144477735"
    assinatura.email_de_cobranca = "contato@evolury.com.br"
    assinatura.save()
    return assinatura


def por_caminho(chamadas, caminho):
    return next((c for c in chamadas if c["caminho"] == caminho), None)


@pytest.mark.contract
class TestDadosDeCobranca:
    def test_documento_invalido_e_recusado_na_hora(self, session_client, workspace):
        resposta = session_client.post(
            DADOS_URL.format(slug=workspace.slug),
            {"nome": "Fulano", "cpf_cnpj": "123.456.789-00", "email": "a@b.com"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error_message"] == "DOCUMENTO_INVALIDO"

    def test_sem_nome_ou_email_nao_grava(self, session_client, workspace):
        resposta = session_client.post(
            DADOS_URL.format(slug=workspace.slug), {"cpf_cnpj": CPF}, format="json"
        )

        assert resposta.data["error_message"] == "DADOS_INCOMPLETOS"

    def test_guarda_so_digito_e_devolve_formatado(self, session_client, workspace):
        session_client.post(
            DADOS_URL.format(slug=workspace.slug),
            {"nome": "Evolury LTDA", "cpf_cnpj": CPF, "email": "contato@evolury.com.br"},
            format="json",
        )

        workspace.assinatura.refresh_from_db()
        assert workspace.assinatura.cpf_cnpj == "11144477735"

        lido = session_client.get(DADOS_URL.format(slug=workspace.slug))
        assert lido.data["cpf_cnpj"] == CPF
        assert lido.data["completo"] is True


@pytest.mark.contract
class TestCupom:
    def test_codigo_que_nao_existe(self, session_client, workspace):
        resposta = session_client.post(CUPOM_URL.format(slug=workspace.slug), {"codigo": "NAOEXISTE"}, format="json")

        assert resposta.data["error_message"] == "CUPOM_INVALIDO"

    def test_vencido_diz_que_venceu(self, session_client, workspace):
        Cupom.objects.create(
            codigo="ONTEM", tipo=cupons.PERCENTUAL, valor=50, validade=timezone.now().date() - timedelta(days=1)
        )

        resposta = session_client.post(CUPOM_URL.format(slug=workspace.slug), {"codigo": "ontem"}, format="json")

        assert resposta.data["error_message"] == "CUPOM_VENCIDO"

    def test_esgotado_diz_que_esgotou(self, session_client, workspace):
        Cupom.objects.create(codigo="ULTIMO", tipo=cupons.PERCENTUAL, valor=10, usos_max=1, usos=1)

        resposta = session_client.post(CUPOM_URL.format(slug=workspace.slug), {"codigo": "ULTIMO"}, format="json")

        assert resposta.data["error_message"] == "CUPOM_ESGOTADO"

    def test_valido_devolve_o_que_a_tela_precisa(self, session_client, workspace):
        Cupom.objects.create(codigo="LANCAMENTO", tipo=cupons.PERCENTUAL, valor=30, ciclos=3)

        resposta = session_client.post(
            CUPOM_URL.format(slug=workspace.slug), {"codigo": "lancamento"}, format="json"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["tipo"] == cupons.PERCENTUAL
        assert resposta.data["valor"] == 30


@pytest.mark.contract
class TestContratar:
    def test_sem_dados_de_cobranca_nao_contrata(self, session_client, workspace, enviado):
        resposta = session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "pix"},
            format="json",
        )

        assert resposta.data["error_message"] == "DADOS_DE_COBRANCA_FALTANDO"
        assert enviado == []

    @pytest.mark.parametrize(
        "corpo,esperado",
        [
            ({"plano": "premium", "ciclo": "mensal", "forma": "pix"}, "PLANO_INVALIDO"),
            ({"plano": "profissional", "ciclo": "quinzenal", "forma": "pix"}, "CICLO_INVALIDO"),
            ({"plano": "profissional", "ciclo": "mensal", "forma": "boleto"}, "FORMA_INVALIDA"),
        ],
    )
    def test_escolhas_invalidas(self, session_client, workspace, com_dados, enviado, corpo, esperado):
        resposta = session_client.post(CONTRATAR_URL.format(slug=workspace.slug), corpo, format="json")

        assert resposta.data["error_message"] == esperado
        assert enviado == []

    def test_pix_cria_cliente_e_assinatura(self, session_client, workspace, com_dados, enviado):
        resposta = session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "pix"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["forma"] == "pix"
        assert resposta.data["link"].endswith("/pay_001")

        cliente = por_caminho(enviado, "customers")
        assert cliente["corpo"]["cpfCnpj"] == "11144477735"
        assert cliente["corpo"]["externalReference"] == f"qoowork:{workspace.id}"

        assinatura_enviada = por_caminho(enviado, "subscriptions")
        # R$ 690,00 vão como 690.0, e o ciclo como o Asaas o chama.
        assert assinatura_enviada["corpo"]["value"] == 690.0
        assert assinatura_enviada["corpo"]["cycle"] == "MONTHLY"
        assert assinatura_enviada["corpo"]["billingType"] == "PIX"

        com_dados.refresh_from_db()
        assert com_dados.asaas_customer_id == "cus_001"
        assert com_dados.asaas_subscription_id == "sub_001"
        assert com_dados.plano == PROFISSIONAL

    def test_cartao_vai_para_o_checkout_do_asaas(self, session_client, workspace, com_dados, enviado):
        resposta = session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "cartao"},
            format="json",
        )

        assert resposta.data["link"].startswith("https://asaas.com/checkout/")
        checkout = por_caminho(enviado, "checkouts")
        # Só cartão: `RECURRENT` do Asaas não aceita PIX.
        assert checkout["corpo"]["billingTypes"] == ["CREDIT_CARD"]
        assert checkout["corpo"]["chargeTypes"] == ["RECURRENT"]
        assert checkout["corpo"]["subscription"]["cycle"] == "MONTHLY"
        assert por_caminho(enviado, "subscriptions") is None

    def test_o_acesso_nao_e_liberado_pela_contratacao(self, session_client, workspace, com_dados, enviado):
        """Quem volta do checkout pode fechar a aba. Só o webhook prova pagamento."""
        antes = com_dados.status

        session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "cartao"},
            format="json",
        )

        com_dados.refresh_from_db()
        assert com_dados.status == antes

    def test_cortesia_libera_na_hora_e_tem_fim(self, session_client, workspace, com_dados, enviado):
        Cupom.objects.create(codigo="TESTE30", tipo=cupons.CORTESIA, valor=30)
        hoje = timezone.now().date()

        resposta = session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "pix", "cupom": "teste30"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        com_dados.refresh_from_db()
        assert com_dados.status == regua.EM_CORTESIA
        assert com_dados.pago_ate == hoje + timedelta(days=30)
        assert com_dados.promocao_termina_em == hoje + timedelta(days=30)
        # A cobrança só vence quando a cortesia acabar, e vale zero até lá.
        assinatura_enviada = por_caminho(enviado, "subscriptions")
        assert assinatura_enviada["corpo"]["nextDueDate"] == (hoje + timedelta(days=30)).isoformat()
        assert assinatura_enviada["corpo"]["value"] == 0.0

    def test_cupom_percentual_desconta_o_que_vai_para_o_asaas(self, session_client, workspace, com_dados, enviado):
        Cupom.objects.create(codigo="METADE", tipo=cupons.PERCENTUAL, valor=50, ciclos=2)

        session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "pix", "cupom": "METADE"},
            format="json",
        )

        assert por_caminho(enviado, "subscriptions")["corpo"]["value"] == 345.0
        com_dados.refresh_from_db()
        assert com_dados.promocao_termina_em is not None
        assert Cupom.objects.get(codigo="METADE").usos == 1

    def test_asaas_recusando_volta_com_o_motivo(self, session_client, workspace, com_dados, mocker):
        from plane.utils.asaas import ErroDoAsaas

        mocker.patch(
            "plane.utils.asaas.configuracao",
            return_value={"chave": "x", "ambiente": "producao", "token_do_webhook": "t"},
        )
        mocker.patch(
            "plane.utils.asaas._requisitar",
            side_effect=ErroDoAsaas("400", status=400, corpo={"errors": [{"description": "CPF inválido"}]}),
        )

        resposta = session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "pix"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_502_BAD_GATEWAY
        assert "CPF inválido" in str(resposta.data["detalhe"])

    def test_a_contratacao_fica_no_historico(self, session_client, workspace, com_dados, enviado):
        session_client.post(
            CONTRATAR_URL.format(slug=workspace.slug),
            {"plano": PROFISSIONAL, "ciclo": CICLO_MENSAL, "forma": "pix"},
            format="json",
        )

        assert HistoricoDeAssinatura.objects.filter(evento="contratacao").exists()


@pytest.mark.contract
class TestTrocarDePlano:
    @pytest.fixture
    def assinado(self, com_dados):
        for campo, valor in copia_para_contrato(ESSENCIAL, CICLO_MENSAL).items():
            setattr(com_dados, campo, valor)
        com_dados.status = regua.ATIVA
        com_dados.pago_ate = timezone.now().date() + timedelta(days=15)
        com_dados.asaas_customer_id = "cus_001"
        com_dados.asaas_subscription_id = "sub_001"
        com_dados.save()
        return com_dados

    def test_upgrade_vale_agora_e_cobra_so_a_diferenca(self, session_client, workspace, assinado, enviado):
        resposta = session_client.post(
            TROCAR_URL.format(slug=workspace.slug), {"plano": PROFISSIONAL}, format="json"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["imediato"] is True
        assinado.refresh_from_db()
        assert assinado.plano == PROFISSIONAL

        avulsa = por_caminho(enviado, "payments")
        # Metade do ciclo restante sobre a diferença de R$ 400,00.
        assert 0 < avulsa["corpo"]["value"] < 400.0
        assert por_caminho(enviado, "subscriptions/sub_001")["corpo"]["value"] == 690.0

    def test_downgrade_com_o_espaco_cheio_diz_o_que_precisa_sair(
        self, session_client, workspace, create_user, enviado
    ):
        assinatura = workspace.assinatura
        for campo, valor in copia_para_contrato(AVANCADO, CICLO_MENSAL).items():
            setattr(assinatura, campo, valor)
        assinatura.nome_de_cobranca = "Evolury"
        assinatura.cpf_cnpj = "11144477735"
        assinatura.status = regua.ATIVA
        assinatura.save()

        projeto = Project.objects.create(
            name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user
        )
        ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
        State.objects.filter(project=projeto).delete()
        from plane.db.models import Automation

        for indice in range(3):
            Automation.objects.create(
                project=projeto,
                workspace=workspace,
                name=f"Regra {indice}",
                trigger_type="work_item_created",
                trigger_config={},
                actions=[{"type": "set_priority", "config": {"priority": "high"}}],
                is_active=True,
            )

        resposta = session_client.post(
            TROCAR_URL.format(slug=workspace.slug), {"plano": ESSENCIAL}, format="json"
        )

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.data["error_message"] == "ACIMA_DO_TETO"
        assert resposta.data["precisa_sair"]["automacoes"] == 1

    def test_downgrade_cabendo_no_teto_vale_no_proximo_ciclo(self, session_client, workspace, enviado):
        assinatura = workspace.assinatura
        for campo, valor in copia_para_contrato(PROFISSIONAL, CICLO_MENSAL).items():
            setattr(assinatura, campo, valor)
        assinatura.nome_de_cobranca = "Evolury"
        assinatura.cpf_cnpj = "11144477735"
        assinatura.status = regua.ATIVA
        assinatura.asaas_subscription_id = "sub_001"
        assinatura.save()

        resposta = session_client.post(
            TROCAR_URL.format(slug=workspace.slug), {"plano": ESSENCIAL}, format="json"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["imediato"] is False
        # Downgrade não gera crédito nem cobrança avulsa.
        assert por_caminho(enviado, "payments") is None

    def test_trocar_para_o_mesmo_plano_e_recusado(self, session_client, workspace, assinado, enviado):
        resposta = session_client.post(TROCAR_URL.format(slug=workspace.slug), {"plano": ESSENCIAL}, format="json")

        assert resposta.data["error_message"] == "MESMO_PLANO"


@pytest.mark.contract
class TestHistoricoDeCobrancas:
    def test_lista_do_espelho_local(self, session_client, workspace, com_dados):
        Cobranca.objects.create(
            assinatura=com_dados,
            asaas_payment_id="pay_001",
            status="RECEIVED",
            forma="PIX",
            valor=69000,
            vencimento=date(2026, 8, 22),
            link="https://asaas.com/i/pay_001",
        )

        resposta = session_client.get(COBRANCAS_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK
        assert len(resposta.data) == 1
        assert resposta.data[0]["valor"] == 69000
        assert resposta.data[0]["link"].endswith("pay_001")
