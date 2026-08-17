#!/usr/bin/env bash
#
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Roda aqui tudo o que a CI roda num pull request.
#
# Por que existe: o princípio é que nenhuma checagem que barra um PR deva ser
# descoberta só depois do PR aberto. Ele nasceu de uma falha concreta — o lint
# da API reprovou por uma linha de 121 colunas, e a bateria local tinha passado
# porque `pnpm check` cobre só o lado JavaScript. A API não é pacote do turbo, e
# o copyright é um binário Go: cada um estava fora do alcance por um motivo
# diferente, e o resultado era o mesmo.
#
# O que fica de fora, e por quê:
#
#   codeql        exige licença do GitHub Code Security. O repositório é privado,
#                 então o CLI não pode ser usado nem aqui nem lá sem ela — não é
#                 questão de ferramenta faltando, é de licença.
#   check-version compara a versão do PR com a do main. Só faz sentido numa
#                 ramificação de release, e é conferida no momento do corte.
#   build-branch  publica imagem; não barra PR.
#
# Uso:
#   bin/verificar.sh           # tudo
#   bin/verificar.sh --rapido  # pula o build e os testes da API
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

RAPIDO=0
[ "${1:-}" = "--rapido" ] && RAPIDO=1

FALHAS=()

passo() {
  local nome="$1"; shift
  echo
  echo "▸ $nome"
  if "$@"; then
    echo "  ✓ $nome"
  else
    echo "  ✗ $nome"
    FALHAS+=("$nome")
  fi
}

passo "formato, lint e tipos (web)" pnpm check
passo "lint da API" bash bin/lint-api.sh
passo "cabeçalhos de copyright" bash bin/copyright.sh
passo "idiomas entre si" pnpm dlx tsx packages/i18n/scripts/sync-check.ts --ci
passo "chaves usadas no código" pnpm dlx tsx packages/i18n/scripts/chaves-usadas.ts --ci

if [ $RAPIDO -eq 0 ]; then
  passo "build" pnpm build
  passo "testes da API" bash bin/testes-api.sh -q
fi

echo
if [ ${#FALHAS[@]} -eq 0 ]; then
  echo "✓ tudo o que a CI confere está verde aqui"
  exit 0
fi
echo "✗ ${#FALHAS[@]} checagem(ns) reprovada(s): ${FALHAS[*]}"
echo "  a CI vai reprovar igual — corrija antes de abrir o PR"
exit 1
