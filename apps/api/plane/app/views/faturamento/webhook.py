# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A porta por onde o Asaas fala com o QooWork — ver ADR 0021.

**Grava e responde 200. Sempre.** Não é preguiça de tratar erro: quinze
respostas de erro seguidas **interrompem a fila** do Asaas, e a fila é da conta
inteira. A conta da Evolury atende outros negócios — 9 assinaturas ativas e 259
cobranças que não são do QooWork, medidas em 21/08/2026 —, de modo que um erro
nosso calaria a cobrança deles também. O processamento acontece depois, em fila
nossa, onde falhar só atrasa o que é nosso.

**A idempotência é o `id` do evento.** O Asaas entrega *at-least-once* e
reenvia a fila inteira quando ela é reativada: receber duas vezes é o caso
normal, não a exceção.

Esta rota é pública de propósito — quem prova quem é são os 32 a 255 caracteres
do `asaas-access-token`, comparados em tempo constante.
"""

import json
from hmac import compare_digest

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from plane.bgtasks.faturamento_evento import processar_evento_do_asaas
from plane.db.models import EventoAsaas
from plane.utils.asaas import configuracao

# Quando o último evento chegou. O alarme lê daqui para descobrir fila
# interrompida — que é silenciosa por natureza.
CHAVE_DO_ULTIMO_EVENTO = "faturamento:ultimo_evento_em"


@csrf_exempt
def webhook_do_asaas(request):
    if request.method != "POST":
        return JsonResponse({"error": "METODO_NAO_PERMITIDO"}, status=405)

    esperado = configuracao()["token_do_webhook"]
    recebido = request.headers.get("asaas-access-token", "")
    # Instância sem token configurado recusa tudo. O contrário — aceitar
    # enquanto ninguém configurou — deixaria qualquer um forjar um pagamento.
    if not esperado or not compare_digest(str(esperado), str(recebido)):
        return JsonResponse({"error": "TOKEN_INVALIDO"}, status=401)

    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        # Corpo ilegível não volta como erro: voltaria para sempre, porque o
        # Asaas reenvia o mesmo corpo.
        return JsonResponse({"recebido": False, "motivo": "CORPO_INVALIDO"}, status=200)

    identificador = payload.get("id")
    if not identificador:
        return JsonResponse({"recebido": False, "motivo": "SEM_ID"}, status=200)

    evento, criado = EventoAsaas.objects.get_or_create(
        asaas_event_id=identificador,
        defaults={"tipo": payload.get("event", ""), "payload": payload},
    )

    cache.set(CHAVE_DO_ULTIMO_EVENTO, timezone.now().isoformat(), None)

    if criado:
        processar_evento_do_asaas.delay(str(evento.id))

    return JsonResponse({"recebido": True, "repetido": not criado}, status=200)
