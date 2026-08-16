#!/usr/bin/env bash
#
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Roda o mesmo lint que a CI roda na API.
#
# Por que existe: `pnpm check` cobre só o lado JavaScript — a API não é um
# pacote do turbo, então o linter dela não tinha entrada local nenhuma. O
# resultado previsível aconteceu: uma linha longa passou por toda a bateria
# local e só apareceu na CI, depois do PR aberto.
#
# Contêiner descartável em vez da pilha de teste: linter não precisa de banco,
# fila nem storage, e subir tudo isso para ler arquivo seria pagar minutos por
# nada.
#
# Uso:
#   bin/lint-api.sh          # confere
#   bin/lint-api.sh --fix    # conserta o que dá
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker run --rm \
  -v "$RAIZ/apps/api:/code" \
  -w /code \
  python:3.12-slim \
  sh -c "pip install --quiet ruff && ruff check ${*:-}"
CODIGO=$?

if [ $CODIGO -eq 0 ]; then
  echo "✓ lint da API limpo"
else
  echo "✗ lint da API reprovou (código $CODIGO) — a CI vai reprovar igual"
fi
exit $CODIGO
