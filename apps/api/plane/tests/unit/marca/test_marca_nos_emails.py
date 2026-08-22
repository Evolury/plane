# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O e-mail que sai daqui é do QooWork, e não de outro produto.

O ADR 0020 decidiu QooWork "em tudo que o usuário vê", e listou a assinatura
dos e-mails. Mesmo assim, até 22/08/2026, o convite que um cliente pagante
recebia trazia assunto "…on Plane", o logotipo do Plane servido de
`media.docs.plane.so`, e um rodapé com 37 links para o X, o LinkedIn, o GitHub
e o fórum do Plane.

Nada disso aparece em teste de comportamento: o e-mail sai, o cliente recebe,
o cadastro funciona. Só aparece lendo a mensagem — e quando alguém lê, já foi
para o cliente. Daí uma guarda que lê os arquivos.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings

# `plane/settings/common.py` define `BASE_DIR` como a raiz da API — os modelos
# ficam FORA do pacote `plane`, em `apps/api/templates`. Contar `parents` daqui
# já errou uma vez, e o teste seguinte (o que exige ao menos dez modelos) foi
# quem pegou: sem ele, a lista vazia teria feito toda a parametrização passar
# sem ler arquivo nenhum.
RAIZ_DA_API = Path(settings.BASE_DIR).parent
MODELOS = RAIZ_DA_API / "templates" / "emails"
TAREFAS = Path(settings.BASE_DIR) / "bgtasks"

# Endereços do produto de origem. Nenhum tem o que fazer num e-mail nosso.
ENDERECOS_DO_PLANE = re.compile(
    r"x\.com/planepowers|linkedin\.com/company/planepowers|github\.com/makeplane|"
    r"forum\.plane\.so|plane\.so/|plane\.sh/|media\.docs\.plane\.so|plane-marketing\.s3"
)

# Exceção única, e por um motivo concreto: `issue-updates.html` usa doze ícones
# funcionais (estado, prioridade, etiqueta, prazo) hospedados no S3 de
# marketing do Plane. Não são marca — são pictogramas —, mas são dependência de
# terceiro e entregam o IP de quem abre o e-mail. Sair deles exige hospedar os
# doze arquivos em `plane/static`, e isso não entrou em 22/08/2026. A exceção
# está aqui nomeada para que a dívida tenha dono, e não para que ela suma.
EXCECOES = {"notifications/issue-updates.html": "plane-marketing.s3"}


def _modelos():
    return sorted(MODELOS.rglob("*.html"))


def test_ha_modelos_para_conferir():
    """Sem isto, apagar a pasta faria a suíte inteira passar em silêncio."""
    assert len(_modelos()) >= 10


@pytest.mark.parametrize("modelo", _modelos(), ids=lambda p: str(p).split("emails/")[1])
def test_modelo_nao_aponta_para_o_plane(modelo):
    relativo = str(modelo).split("emails/")[1]
    texto = modelo.read_text()

    permitido = EXCECOES.get(relativo)
    achados = [
        linha.strip()
        for linha in texto.splitlines()
        if ENDERECOS_DO_PLANE.search(linha) and not (permitido and permitido in linha)
    ]
    assert not achados, f"{relativo} ainda leva o leitor ao Plane:\n" + "\n".join(achados[:5])


def test_assunto_de_email_nao_diz_plane():
    achados = []
    for arquivo in sorted(TAREFAS.glob("*.py")):
        for numero, linha in enumerate(arquivo.read_text().splitlines(), 1):
            if "subject" in linha and re.search(r"\bPlane\b", linha):
                achados.append(f"{arquivo.name}:{numero} {linha.strip()}")
    assert not achados, "assunto de e-mail ainda diz Plane:\n" + "\n".join(achados)


def test_o_nome_do_produto_vem_de_um_lugar_so():
    from plane.utils import marca

    assert marca.NOME == "QooWork"
