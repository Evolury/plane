# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Mixins for Django REST Framework views.
"""

# Third party imports
from rest_framework.exceptions import NotFound


class ReadReplicaControlMixin:
    """
    Mixin to control read replica usage in DRF views.
    Set use_read_replica = True/False to route read operations to
    replica/primary database. Works with ReadReplicaRoutingMiddleware.
    Usage:
        class MyViewSet(ReadReplicaControlMixin, ModelViewSet):
            use_read_replica = True  # Use replica for GET requests
    Note:
        - Only affects GET, HEAD, OPTIONS requests
        - Write operations always use primary database
        - Defaults to True for safe replica usage
    """

    use_read_replica: bool = True


# Evolury: a tarefa da URL tem de ser do projeto da URL.
class TarefaPertenceAoProjetoMixin:
    """A permissão olha o projeto da URL; a consulta usava a tarefa da URL.

    O defeito (revisão do upstream, SECUR-243): as vinte e cinco rotas de
    sub-recurso de tarefa trazem projeto E tarefa no caminho, e nada amarrava
    um ao outro. A permissão respondia "sim" porque eu sou membro do projeto A;
    a ação então trabalhava sobre uma tarefa do projeto B, porque ninguém
    perguntou de que projeto ela era.

    Medido antes desta correção, como membro de A apontando para uma tarefa de
    B: comentário, link, reação, inscrição e relação criados na tarefa alheia,
    relação alheia apagada, e a lista de subtarefas de B devolvida na íntegra.

    Por que aqui e não em cada view: a regra é uma só, e escrevê-la vinte e
    cinco vezes é escrevê-la vinte e quatro vezes certo e uma vez errado. Aqui
    ela vale também para a rota que alguém acrescentar amanhã.

    Roda depois da autenticação e da permissão — é `initial`, não `dispatch` —
    então não vira um oráculo de existência para quem nem entrou. Responde 404:
    do ponto de vista de quem pediu, aquela tarefa não existe naquele projeto,
    e 403 confirmaria que ela existe em outro lugar.

    Fica de fora, de propósito, a rota sem projeto no caminho (`my-tasks`, que
    é de workspace) — sem projeto na URL não há o que amarrar.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self._exigir_tarefa_do_projeto()

    def _exigir_tarefa_do_projeto(self):
        project_id = self.kwargs.get("project_id")
        issue_id = self.kwargs.get("issue_id")
        if not project_id or not issue_id:
            return

        # Import tardio: `plane.db.models` importa de volta desta árvore, e no
        # topo do arquivo isto vira ciclo.
        from plane.db.models import Issue

        # `all_objects` de propósito: este guarda responde por UMA pergunta, a
        # de pertencimento. Se a tarefa está excluída, quem recusa é a consulta
        # da própria view, como sempre foi — não é assunto daqui.
        if not Issue.all_objects.filter(pk=issue_id, project_id=project_id).exists():
            raise NotFound({"error": "Tarefa não encontrada neste projeto."})
