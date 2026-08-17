# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Core mixins for Django and Django REST Framework views.

Evolury: nasceu só com o controle de réplica de leitura; hoje guarda também o
recorte de tarefa por projeto, que as duas APIs — a do app e a pública —
precisam aplicar do mesmo jeito.
"""

from .view import ReadReplicaControlMixin, TarefaPertenceAoProjetoMixin

__all__ = [
    "ReadReplicaControlMixin",
    "TarefaPertenceAoProjetoMixin",
]
