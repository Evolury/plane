#!/usr/bin/env bash
#
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Roda o mesmo `addlicense` que a CI roda, com os mesmos argumentos.
#
# Por que existe: era a única checagem de PR sem entrada local depois do lint da
# API — e é a que mais tem chance de reprovar num lote grande, porque basta um
# arquivo novo nascer sem cabeçalho. Descobrir isso depois do PR aberto custa um
# ciclo de CI inteiro por um comentário de três linhas.
#
# Contêiner descartável: `addlicense` é um binário Go, e instalar Go na máquina
# para conferir cabeçalho seria caro pelo que entrega.
#
# Uso:
#   bin/copyright.sh          # confere
#   bin/copyright.sh --fix    # escreve o cabeçalho onde falta
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

# `-check` confere; sem ele, o addlicense ESCREVE. O padrão é conferir.
MODO="-check"
[ "${1:-}" = "--fix" ] && MODO=""

docker run --rm -v "$RAIZ:/repo" -w /repo golang:1.24-alpine sh -c "
  apk add --no-cache git >/dev/null 2>&1
  git config --global --add safe.directory /repo
  go install github.com/google/addlicense@latest >/dev/null 2>&1
  export PATH=\$PATH:/go/bin
  addlicense $MODO -f COPYRIGHT.txt -ignore '**/migrations/**' \$(git ls-files '*.py') &&
  addlicense $MODO -f COPYRIGHT.txt -ignore '**/*.config.ts' -ignore '**/*.d.ts' \$(git ls-files '*.ts' '*.tsx')
"
CODIGO=$?

if [ $CODIGO -eq 0 ]; then
  echo "✓ cabeçalhos de copyright em ordem"
else
  echo "✗ faltam cabeçalhos (código $CODIGO) — 'bin/copyright.sh --fix' escreve"
fi
exit $CODIGO
