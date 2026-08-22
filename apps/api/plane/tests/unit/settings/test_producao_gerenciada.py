# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O que muda quando o banco e os arquivos não são mais nossos (ADR 0022).

Três ajustes pequenos, e os três com a mesma característica: quebram **em
produção, sob carga**, e nunca no desenvolvimento. Cursor de servidor só falha
numa exportação grande; ACL só falha no caminho de upload que o produto quase
não usa; o agendador no banco só custa dinheiro quando o banco cobra por estar
acordado.

Por isso os três têm teste: nenhum deles tem chance de ser notado por quem
estiver olhando a tela.
"""

import os
import subprocess
import sys

import pytest
from django.conf import settings

from plane.celery import app


def _valor_das_settings(expressao, **ambiente):
    """Lê uma configuração num processo próprio, com o ambiente pedido.

    Reimportar as settings no processo do teste contaminaria os outros: elas
    montam middleware, roteador de banco e cache. Um subprocesso é o preço
    honesto de conferir um caminho que depende de variável de ambiente.
    """
    codigo = (
        "import django, os;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plane.settings.test');"
        "django.setup();"
        "from django.conf import settings;"
        f"print({expressao})"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        env={**os.environ, **ambiente},
    )
    assert resultado.returncode == 0, resultado.stderr[-800:]
    return resultado.stdout.strip()


@pytest.mark.unit
class TestBancoComPooler:
    def test_por_padrao_o_cursor_de_servidor_continua_ligado(self):
        """Instância com Postgres próprio não deve perder varredura em partes."""
        assert (
            _valor_das_settings(
                "settings.DATABASES['default'].get('DISABLE_SERVER_SIDE_CURSORS', False)",
                BANCO_COM_POOLER="0",
            )
            == "False"
        )

    def test_com_pooler_o_cursor_de_servidor_e_desligado(self):
        """No PgBouncer em modo transação o cursor nomeado não sobrevive."""
        assert (
            _valor_das_settings(
                "settings.DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS']",
                BANCO_COM_POOLER="1",
            )
            == "True"
        )


@pytest.mark.unit
class TestArmazenamentoSemACL:
    def test_nenhuma_acl_e_enviada(self):
        """O R2 não implementa ACL de objeto: mandar é erro, não opção ignorada."""
        assert settings.AWS_DEFAULT_ACL is None

    def test_o_balde_continua_privado(self):
        # Sem `querystring_auth` o django-storages geraria URL crua; o produto
        # não depende disso — quem serve arquivo é a URL assinada do
        # `S3Storage`. O que este teste guarda é que ninguém volte a marcar
        # objeto como público achando que é necessário.
        assert settings.AWS_DEFAULT_ACL is None
        assert settings.AWS_S3_FILE_OVERWRITE is False


@pytest.mark.unit
class TestAgendaEmArquivo:
    def test_o_agendador_nao_consulta_o_banco(self):
        """O `DatabaseScheduler` bate no banco a cada poucos segundos.

        Num banco que dorme quando ninguém o usa, essa batida é a diferença
        entre pagar pelo que se usa e pagar por estar ligado.
        """
        assert "DatabaseScheduler" not in str(app.conf.beat_scheduler or "")

    def test_a_agenda_tem_um_arquivo_para_lembrar_o_ultimo_disparo(self):
        # Sem arquivo, o agendador esquece o que já rodou a cada reinício.
        assert app.conf.beat_schedule_filename

    def test_a_agenda_continua_vindo_do_codigo(self):
        # A fonte da verdade é `beat_schedule`, versionada junto do código —
        # e é por isso que trocar o agendador não perde nenhuma tarefa.
        assert len(app.conf.beat_schedule) >= 10
