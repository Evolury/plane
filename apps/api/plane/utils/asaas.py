# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O cliente do Asaas — ver ADR 0021.

**Uma única função de transporte.** Todo o resto do módulo passa por
`_requisitar`, e é isso que permite a suíte inteira rodar sem rede: o teste
substitui um ponto, não trinta. Nenhum teste deste repositório fala com o
Asaas — e agora isso deixou de ser higiene e virou obrigação, porque a chave é
de **produção**.

**A conta do Asaas não é só do QooWork.** Medido na conta da Evolury em
21/08/2026: 9 assinaturas ativas, 25 clientes e 259 cobranças que pertencem a
outros negócios da empresa. Duas consequências que atravessam este módulo:

1. O que criamos leva `externalReference` com o prefixo `qoowork:`, para que o
   caminho de volta não dependa de adivinhação.
2. O webhook recebe **tudo** — inclusive o que não é nosso. Ignorar é o
   comportamento certo; errar não é, porque quinze erros seguidos interrompem a
   fila do Asaas e calam também a cobrança dos outros negócios.

**Dinheiro.** O Asaas fala em reais com casa decimal (`2000.0`); nós guardamos
centavos inteiros. A conversão mora aqui, e passa por `Decimal` — `2000.0 * 100`
em ponto flutuante é a origem clássica do centavo perdido.
"""

from decimal import Decimal
from typing import Optional

import requests

from plane.license.utils.instance_value import get_configuration_value

BASE_PRODUCAO = "https://api.asaas.com/v3"
BASE_SANDBOX = "https://api-sandbox.asaas.com/v3"

TEMPO_LIMITE = 20

# O prefixo que separa o que é nosso do que é dos outros negócios da conta.
PREFIXO_DE_REFERENCIA = "qoowork:"


class ErroDoAsaas(Exception):
    """Falha de comunicação ou recusa do Asaas, com o corpo preservado."""

    def __init__(self, mensagem, status=None, corpo=None):
        super().__init__(mensagem)
        self.status = status
        self.corpo = corpo


def configuracao():
    """Chave, ambiente e token do webhook, da configuração da instância."""
    chave, ambiente, token = get_configuration_value(
        [
            {"key": "ASAAS_API_KEY", "default": ""},
            {"key": "ASAAS_AMBIENTE", "default": "producao"},
            {"key": "ASAAS_WEBHOOK_TOKEN", "default": ""},
        ]
    )
    return {"chave": chave or "", "ambiente": ambiente or "producao", "token_do_webhook": token or ""}


def base_da_api(ambiente: Optional[str] = None) -> str:
    if ambiente is None:
        ambiente = configuracao()["ambiente"]
    return BASE_SANDBOX if ambiente == "sandbox" else BASE_PRODUCAO


def referencia_de(workspace_id) -> str:
    return f"{PREFIXO_DE_REFERENCIA}{workspace_id}"


def espaco_da_referencia(referencia) -> Optional[str]:
    """O id do espaço dentro de um `externalReference`, ou `None` se não for nosso."""
    if not referencia or not str(referencia).startswith(PREFIXO_DE_REFERENCIA):
        return None
    return str(referencia)[len(PREFIXO_DE_REFERENCIA) :]


def centavos(valor) -> int:
    """Reais do Asaas para centavos nossos, sem passar por ponto flutuante."""
    if valor is None:
        return 0
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1")))


def reais(valor_em_centavos: int) -> float:
    """Centavos nossos para o número que o Asaas espera."""
    return float(Decimal(valor_em_centavos) / 100)


def _requisitar(metodo: str, caminho: str, corpo=None, parametros=None):
    """O único ponto que fala com a rede. Substituí-lo é como os testes rodam."""
    configurado = configuracao()
    if not configurado["chave"]:
        raise ErroDoAsaas("O Asaas não está configurado nesta instância (ASAAS_API_KEY vazia).")

    resposta = requests.request(
        metodo,
        f"{base_da_api(configurado['ambiente'])}/{caminho.lstrip('/')}",
        json=corpo,
        params=parametros,
        headers={
            "access_token": configurado["chave"],
            "Content-Type": "application/json",
            # O Asaas pede identificação do integrador nos cabeçalhos.
            "User-Agent": "QooWork",
        },
        timeout=TEMPO_LIMITE,
    )

    try:
        dados = resposta.json()
    except ValueError:
        dados = {}

    if resposta.status_code >= 400:
        raise ErroDoAsaas(
            f"{metodo} {caminho} devolveu {resposta.status_code}",
            status=resposta.status_code,
            corpo=dados,
        )

    return dados


# --- clientes -------------------------------------------------------------


def criar_cliente(*, nome, cpf_cnpj, email, workspace_id, telefone=""):
    return _requisitar(
        "POST",
        "customers",
        {
            "name": nome,
            "cpfCnpj": cpf_cnpj,
            "email": email,
            "mobilePhone": telefone,
            "externalReference": referencia_de(workspace_id),
        },
    )


def buscar_cliente(cliente_id):
    return _requisitar("GET", f"customers/{cliente_id}")


# --- assinaturas ----------------------------------------------------------


def criar_assinatura(
    *,
    cliente_id,
    valor_em_centavos,
    ciclo_asaas,
    primeiro_vencimento,
    descricao,
    workspace_id,
    forma="PIX",
):
    return _requisitar(
        "POST",
        "subscriptions",
        {
            "customer": cliente_id,
            "billingType": forma,
            "value": reais(valor_em_centavos),
            "nextDueDate": primeiro_vencimento,
            "cycle": ciclo_asaas,
            "description": descricao,
            "externalReference": referencia_de(workspace_id),
        },
    )


def atualizar_assinatura(assinatura_id, **campos):
    # `updatePendingPayments` fica de fora de propósito: cobrança já gerada não
    # muda de valor no meio do caminho (ADR 0021).
    return _requisitar("PUT", f"subscriptions/{assinatura_id}", campos)


def cancelar_assinatura(assinatura_id):
    return _requisitar("DELETE", f"subscriptions/{assinatura_id}")


def buscar_assinatura(assinatura_id):
    return _requisitar("GET", f"subscriptions/{assinatura_id}")


def listar_cobrancas(*, assinatura_id=None, limite=20, deslocamento=0):
    parametros = {"limit": limite, "offset": deslocamento}
    if assinatura_id:
        parametros["subscription"] = assinatura_id
    return _requisitar("GET", "payments", parametros=parametros)


def criar_cobranca_avulsa(*, cliente_id, valor_em_centavos, vencimento, descricao, workspace_id, forma="PIX"):
    """A diferença proporcional de um upgrade, por exemplo."""
    return _requisitar(
        "POST",
        "payments",
        {
            "customer": cliente_id,
            "billingType": forma,
            "value": reais(valor_em_centavos),
            "dueDate": vencimento,
            "description": descricao,
            "externalReference": referencia_de(workspace_id),
        },
    )


# --- checkout -------------------------------------------------------------


def criar_checkout(*, valor_em_centavos, descricao, ciclo_asaas, primeiro_vencimento, workspace_id, retorno):
    """Cartão recorrente pela página do Asaas — dado de cartão não passa por nós.

    Só cartão: `chargeTypes: RECURRENT` do Asaas não aceita PIX. O PIX
    recorrente é assinatura com cobrança por ciclo, criada pela API.
    """
    return _requisitar(
        "POST",
        "checkouts",
        {
            "billingTypes": ["CREDIT_CARD"],
            "chargeTypes": ["RECURRENT"],
            "minutesToExpire": 60,
            "externalReference": referencia_de(workspace_id),
            "callback": {
                "successUrl": retorno.get("sucesso"),
                "cancelUrl": retorno.get("cancelado"),
                "expiredUrl": retorno.get("expirado"),
            },
            "items": [{"name": descricao, "quantity": 1, "value": reais(valor_em_centavos)}],
            "subscription": {"cycle": ciclo_asaas, "nextDueDate": primeiro_vencimento},
        },
    )


# --- webhook --------------------------------------------------------------


def listar_webhooks():
    return _requisitar("GET", "webhooks")


def criar_webhook(*, url, token, eventos, nome="QooWork"):
    return _requisitar(
        "POST",
        "webhooks",
        {
            "name": nome,
            "url": url,
            "email": "contato@evolury.com.br",
            "enabled": True,
            "interrupted": False,
            "authToken": token,
            # Sequencial: a ordem dos eventos de uma mesma cobrança importa, e
            # `PAYMENT_RECEIVED` antes de `PAYMENT_CREATED` obrigaria o
            # processador a reconstruir o que o Asaas já sabe.
            "sendType": "SEQUENTIALLY",
            "events": eventos,
        },
    )
