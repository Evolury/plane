# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Cadastra (ou confere) o webhook do QooWork no Asaas — ver ADR 0021.

Existe para que a configuração seja reproduzível: quais eventos, com qual
token, em que ordem de entrega. Feita a mão no painel, ela vira uma decisão que
mora numa aba do navegador de alguém.

Uso:
    python manage.py registrar_webhook_asaas --url https://qoowork.com.br/api/faturamento/asaas/webhook/
    python manage.py registrar_webhook_asaas --conferir
"""

from django.core.management.base import BaseCommand

from plane.utils.asaas import ErroDoAsaas, configuracao, criar_webhook, listar_webhooks

# O que assinamos, e nada além. Assinar tudo encheria a fila — que é da conta
# inteira, com os outros negócios da Evolury dentro — de evento que ignoramos.
EVENTOS = [
    "PAYMENT_CREATED",
    "PAYMENT_UPDATED",
    "PAYMENT_CONFIRMED",
    "PAYMENT_RECEIVED",
    "PAYMENT_OVERDUE",
    "PAYMENT_DELETED",
    "PAYMENT_REFUNDED",
    "PAYMENT_PARTIALLY_REFUNDED",
    "SUBSCRIPTION_UPDATED",
    "SUBSCRIPTION_INACTIVATED",
    "SUBSCRIPTION_DELETED",
    "CHECKOUT_PAID",
    "CHECKOUT_CANCELED",
    "CHECKOUT_EXPIRED",
]


class Command(BaseCommand):
    help = "Cadastra o webhook do faturamento no Asaas, ou lista os que já existem."

    def add_arguments(self, parser):
        parser.add_argument("--url", type=str, help="Endereço público do webhook.")
        parser.add_argument("--conferir", action="store_true", help="Só lista o que já está cadastrado.")

    def handle(self, *args, **opcoes):
        configurado = configuracao()
        if not configurado["chave"]:
            self.stderr.write("ASAAS_API_KEY não está configurada nesta instância.")
            return

        self.stdout.write(f"Ambiente: {configurado['ambiente']}")

        try:
            existentes = listar_webhooks()
        except ErroDoAsaas as erro:
            self.stderr.write(f"Falha ao listar webhooks: {erro}")
            return

        for webhook in existentes.get("data", []):
            estado = "ATIVO" if webhook.get("enabled") else "desligado"
            fila = "INTERROMPIDA" if webhook.get("interrupted") else "ok"
            self.stdout.write(f" · {webhook.get('name')} — {webhook.get('url')} [{estado}, fila {fila}]")

        if opcoes.get("conferir"):
            return

        url = opcoes.get("url")
        if not url:
            self.stderr.write("Informe --url ou use --conferir.")
            return

        if not configurado["token_do_webhook"]:
            self.stderr.write(
                "ASAAS_WEBHOOK_TOKEN não está configurado. Sem ele qualquer um forja um pagamento."
            )
            return

        if any(webhook.get("url") == url for webhook in existentes.get("data", [])):
            self.stdout.write("Já existe um webhook com esse endereço. Nada a fazer.")
            return

        try:
            criado = criar_webhook(url=url, token=configurado["token_do_webhook"], eventos=EVENTOS)
        except ErroDoAsaas as erro:
            self.stderr.write(f"Falha ao criar o webhook: {erro} — {erro.corpo}")
            return

        self.stdout.write(f"Webhook criado: {criado.get('id')} para {criado.get('url')}")
