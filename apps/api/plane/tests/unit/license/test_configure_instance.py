# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A configuração da instância seguindo — ou não — o ambiente.

`configure_instance` usava `get_or_create` e, com isso, **criava o que faltava e
nunca atualizava o que existia**. Como o app lê do banco (`SKIP_ENV_VAR=1`),
trocar uma credencial no ambiente não mudava nada em produção.

Isso mordeu duas vezes em 22/08/2026, no mesmo dia: a chave SMTP do Brevo e a
chave do Asaas — esta recém-rotacionada depois de um vazamento — ficaram velhas
no banco enquanto o ambiente já tinha as novas. As duas foram corrigidas à mão,
uma a uma, e ninguém teria notado até um e-mail não sair ou um pagamento falhar.

O `--sincronizar` é opcional de propósito: o god-mode deixa o administrador
editar essas linhas pela tela, e sincronizar a cada deploy desfaria a edição
dele em silêncio.
"""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from plane.license.models import InstanceConfiguration
from plane.license.utils.encryption import decrypt_data, encrypt_data


def _variaveis(chave, valor, cifrada=False):
    return [{"key": chave, "value": valor, "category": "TESTE", "is_encrypted": cifrada}]


def _rodar(*args):
    saida = StringIO()
    call_command("configure_instance", *args, stdout=saida)
    return saida.getvalue()


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
def test_sem_sincronizar_a_linha_existente_nao_muda():
    """O comportamento antigo continua sendo o padrão."""
    InstanceConfiguration.objects.create(key="ASAAS_API_KEY", value="velha", is_encrypted=False)
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("ASAAS_API_KEY", "nova")):
        saida = _rodar()
    assert InstanceConfiguration.objects.get(key="ASAAS_API_KEY").value == "velha"
    assert "already exists" in saida


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
def test_sincronizar_reescreve_o_que_divergiu():
    InstanceConfiguration.objects.create(key="ASAAS_API_KEY", value="velha", is_encrypted=False)
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("ASAAS_API_KEY", "nova")):
        saida = _rodar("--sincronizar")
    assert InstanceConfiguration.objects.get(key="ASAAS_API_KEY").value == "nova"
    assert "atualizada" in saida


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
def test_sincronizar_lida_com_linha_cifrada():
    """O caso que mordeu de verdade: a chave do Asaas é cifrada no banco."""
    InstanceConfiguration.objects.create(
        key="ASAAS_API_KEY", value=encrypt_data("velha"), is_encrypted=True
    )
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("ASAAS_API_KEY", "nova", cifrada=True)):
        _rodar("--sincronizar")
    linha = InstanceConfiguration.objects.get(key="ASAAS_API_KEY")
    assert decrypt_data(linha.value) == "nova"
    assert linha.is_encrypted is True


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
def test_linha_cifrada_ja_alinhada_nao_e_reescrita():
    """Onde o `decrypt` faz diferença de verdade.

    Comparar o texto cifrado com o texto claro dá "diferente" **sempre** — e o
    teste do caso divergente passaria mesmo assim, porque reescrever também
    chega ao valor certo. O defeito só aparece aqui: sem descriptografar, uma
    linha já alinhada seria reescrita a cada execução e o comando mentiria
    dizendo que atualizou.
    """
    InstanceConfiguration.objects.create(
        key="ASAAS_API_KEY", value=encrypt_data("igual"), is_encrypted=True
    )
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("ASAAS_API_KEY", "igual", cifrada=True)):
        saida = _rodar("--sincronizar")
    # O resumo é o que se afere: dizer `"atualizada" not in saida` casaria com
    # o contador "0 atualizadas" e o teste falharia por motivo errado.
    assert "0 criadas, 0 atualizadas, 1 já alinhadas" in saida


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
def test_ambiente_vazio_nao_apaga_configuracao():
    """Variável não definida neste deploy não pode desligar e-mail ou pagamento."""
    InstanceConfiguration.objects.create(key="EMAIL_HOST_PASSWORD", value="guardada", is_encrypted=False)
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("EMAIL_HOST_PASSWORD", "")):
        saida = _rodar("--sincronizar")
    assert InstanceConfiguration.objects.get(key="EMAIL_HOST_PASSWORD").value == "guardada"
    assert "preservada" in saida


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
def test_simular_nao_grava():
    InstanceConfiguration.objects.create(key="ASAAS_API_KEY", value="velha", is_encrypted=False)
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("ASAAS_API_KEY", "nova")):
        saida = _rodar("--sincronizar", "--simular")
    assert InstanceConfiguration.objects.get(key="ASAAS_API_KEY").value == "velha"
    assert "mudaria" in saida


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
@pytest.mark.parametrize("modo", [("--sincronizar",), ("--sincronizar", "--simular")], ids=["grava", "simula"])
def test_o_valor_nao_aparece_na_saida(modo):
    """Segredo em log de deploy é segredo vazado — já aconteceu nesta casa.

    Os dois caminhos são cobertos porque são duas linhas de escrita diferentes:
    testar só o que grava deixava a mensagem do `--simular` livre para imprimir
    o segredo inteiro.
    """
    InstanceConfiguration.objects.create(key="ASAAS_API_KEY", value="aact_velha_secreta", is_encrypted=False)
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("ASAAS_API_KEY", "aact_nova_secreta")):
        saida = _rodar(*modo)
    assert "aact_velha_secreta" not in saida
    assert "aact_nova_secreta" not in saida


@pytest.mark.django_db
@patch.dict("os.environ", {"SECRET_KEY": "x"})
def test_linha_que_falta_continua_sendo_criada():
    with patch("plane.license.management.commands.configure_instance.instance_config_variables",
               _variaveis("ASAAS_AMBIENTE", "producao")):
        _rodar("--sincronizar")
    assert InstanceConfiguration.objects.get(key="ASAAS_AMBIENTE").value == "producao"
