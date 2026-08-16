# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: motor de automações personalizadas — quando / se / então (ADR 0012).
#
# A divisão dos módulos é a do padrão ECA, e não é enfeite: avaliar e executar
# são preocupações separadas, e é essa separação que permite reaproveitar o
# filtro rico inteiro como condição.
#
#   gatilhos.py  o QUANDO — traduz atividade em evento e casa com a regra
#   condicao.py  o SE      — o filtro do produto aplicado a uma tarefa só
#   acoes.py     o ENTÃO   — o registro de ações, cada uma pelo caminho do produto
#   despacho.py  a porta   — o enxerto barato dentro de `issue_activity`
#   ator.py      o robô    — quem assina as ações e fecha o laço
