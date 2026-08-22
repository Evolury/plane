# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""CPF e CNPJ — ver ADR 0021.

O Asaas exige o documento para criar o cliente, e recusa o inválido. Conferir
aqui antes não é desconfiança dele: é a diferença entre "CPF inválido", dito na
hora em que a pessoa digitou, e um erro genérico de gateway três telas depois.

O dígito verificador é aritmética fechada — não precisa de rede, não muda, e
pega o erro de digitação, que é o caso real. Não prova que o documento existe;
prova que ele **pode** existir.
"""

import re

APENAS_DIGITOS = re.compile(r"\D")


def normalizar(documento: str) -> str:
    """Só os dígitos. Ponto, traço e barra são enfeite de tela."""
    return APENAS_DIGITOS.sub("", documento or "")


def _digito(numeros, pesos) -> int:
    soma = sum(int(numero) * peso for numero, peso in zip(numeros, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(documento: str) -> bool:
    numeros = normalizar(documento)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    primeiro = _digito(numeros[:9], range(10, 1, -1))
    segundo = _digito(numeros[:10], range(11, 1, -1))
    return numeros[9:] == f"{primeiro}{segundo}"


def cnpj_valido(documento: str) -> bool:
    numeros = normalizar(documento)
    if len(numeros) != 14 or numeros == numeros[0] * 14:
        return False
    primeiro = _digito(numeros[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    segundo = _digito(numeros[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return numeros[12:] == f"{primeiro}{segundo}"


def valido(documento: str) -> bool:
    numeros = normalizar(documento)
    if len(numeros) == 11:
        return cpf_valido(numeros)
    if len(numeros) == 14:
        return cnpj_valido(numeros)
    return False


def formatar(documento: str) -> str:
    """Para exibir. Guardar continua sendo só dígito."""
    numeros = normalizar(documento)
    if len(numeros) == 11:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    if len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
    return numeros
