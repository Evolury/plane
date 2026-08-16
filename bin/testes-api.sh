#!/usr/bin/env bash
#
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Roda o pytest da API e DESLIGA a stack de teste ao terminar.
#
# Por que existe: o `docker compose run` sobe banco, redis, fila e storage e os
# deixa de pé depois que o teste acaba. Parados eles não custam nada; de pé,
# custam — o RabbitMQ ocioso já foi medido queimando 171% de CPU nesta máquina,
# indefinidamente, sem atender ninguém.
#
# A parada é `stop`, e não `down`: preserva o banco de teste, então a execução
# seguinte volta em segundos em vez de recriar tudo.
#
# Uso (os argumentos vão direto para o pytest):
#   bin/testes-api.sh
#   bin/testes-api.sh plane/tests/contract/app/test_issue_property_values_app.py
#   bin/testes-api.sh -k icone -q
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

docker compose -f docker-compose-test.yml run --rm api-tests pytest "$@"
# O código de saída do pytest é o que interessa a quem chamou — precisa ser
# guardado ANTES da limpeza, senão o `stop` mascara a falha com o sucesso dele.
CODIGO=$?

docker compose -p planetest stop >/dev/null 2>&1 || true

if [ "$CODIGO" -eq 0 ]; then
  echo "✓ testes verdes — stack de teste parada (sobe sozinha na próxima execução)"
else
  echo "✗ testes falharam (código $CODIGO) — stack de teste parada mesmo assim"
fi
exit "$CODIGO"
