# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""As travas de faturamento que dependem do caminho — ver ADR 0021.

Duas, e as duas pelo mesmo motivo: **não podem ser esquecidas**.

1. **Espaço restrito ou bloqueado lê, mas não escreve.**
2. **A API pública só atende plano que a inclui.**

**Por que middleware, e não permissão em cada view.** Uma trava aplicada view a
view depende de alguém lembrar de aplicá-la, e a view que alguém criar em seis
meses nasceria descoberta. É o mesmo raciocínio do ADR 0008: o que é opcional
não protege nada sozinho. Aqui a trava é o caminho, não o destino.

A segunda trava nasceu no lugar errado e a suíte mostrou: posta como permissão
na view base da API pública, ela foi ignorada por **trinta** views que
sobrescrevem `permission_classes` — o Essencial continuou atendendo pela API,
com 200. Permissão de base que a subclasse apaga sem querer é o retrato do
problema que este arquivo resolve.

**A degradação é o produto, não o castigo.** Restringir para leitura mantém o
dado à vista — e o dado à vista é o motivo de o cliente voltar e pagar.
Suspender tudo de uma vez transforma inadimplência em perda de cliente.

**Exportar sobrevive a tudo.** É a linha que separa "cobrança" de "sequestro de
dado", e por isso está na lista de exceções junto com o próprio faturamento.

Esta é a peça capaz de quebrar o produto inteiro para quem está em dia. Cada
exceção tem teste próprio, e cada estado também.
"""

import re

from django.http import JsonResponse

from plane.utils import direitos, regua
from plane.utils.error_codes import ERROR_CODES
from plane.utils.planos import RECURSO_API_PUBLICA

# `/api/workspaces/<slug>/…` e `/api/v1/workspaces/<slug>/…`, que é a API
# pública. O resto — autenticação, instância, usuário — não tem espaço no
# caminho e não é assunto desta trava.
CAMINHO_DE_ESPACO = re.compile(r"^/api/(?:v1/)?workspaces/(?P<slug>[^/]+)/")

METODOS_DE_LEITURA = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# O que continua funcionando mesmo com o espaço travado. Curta e explícita de
# propósito: uma lista que cresce sozinha deixa de ser exceção e vira regra.
EXCECOES = (
    "faturamento",  # pagar não pode depender de estar pago
    "export-issues",  # exportar sobrevive a todos os estados
    "export-analytics",
)

# Os estados que esta trava aplica. `sem_assinatura` **não** entra: enquanto a
# contratação não existir (E4), aplicá-lo trancaria todo espaço novo num produto
# sem forma de pagar. A régua já diz que ele não escreve; quem passa a cobrar
# isso é a E5, quando houver como contratar.
ESTADOS_TRAVADOS = {
    regua.RESTRITA: "ESPACO_SOMENTE_LEITURA",
    regua.BLOQUEADA: "ESPACO_BLOQUEADO",
    regua.ENCERRADA: "ESPACO_BLOQUEADO",
    regua.REMOVIDA: "ESPACO_BLOQUEADO",
}


class FaturamentoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        encontrado = CAMINHO_DE_ESPACO.match(request.path)
        if encontrado is not None:
            slug = encontrado.group("slug")
            resto = request.path[encontrado.end() :]
            # Espaço inexistente é 404, e quem responde isso é a view.
            if resto.split("/", 1)[0] not in EXCECOES and direitos.existe_espaco(slug=slug):
                recusa = self._recusa_por_plano_da_api(request, slug) or self._recusa_por_estado(
                    request, slug
                )
                if recusa is not None:
                    return recusa

        return self.get_response(request)

    def _recusa_por_plano_da_api(self, request, slug):
        """A API pública é recurso de plano, na leitura e na escrita.

        Vale para `/api/v1/…` e só para ele: as mesmas rotas pelo aplicativo
        continuam abertas, porque quem paga pelo produto não paga de novo para
        usá-lo pela tela.
        """
        if not request.path.startswith("/api/v1/"):
            return None
        if direitos.recurso_liberado(RECURSO_API_PUBLICA, slug=slug):
            return None
        return JsonResponse(direitos.recusa_de_recurso(RECURSO_API_PUBLICA, direitos.plano_de(slug=slug)), status=402)

    def _recusa_por_estado(self, request, slug):
        if request.method in METODOS_DE_LEITURA:
            return None

        estado = direitos.estado(slug=slug)
        codigo = ESTADOS_TRAVADOS.get(estado)
        if codigo is None:
            return None

        return JsonResponse(
            {
                "error_code": ERROR_CODES[codigo],
                "error_message": codigo,
                "status_da_assinatura": estado,
            },
            status=402,
        )
