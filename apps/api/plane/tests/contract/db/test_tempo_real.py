# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O aviso de que uma tarefa mudou (ADR 0013).

Quando uma automação atribuía um responsável, o cartão no quadro não mudava: o
responsável só aparecia recarregando a página. A causa não era a automação — é
que o produto não tinha como dizer ao cliente "mudou algo que não foi você".

O que estes testes trancam é o **contrato do aviso**, e em especial o que ele
NÃO carrega. O evento leva identificadores e nada mais. Mandar o dado da tarefa
obrigaria o servidor a decidir, por destinatário, quem pode ver cada campo — uma
segunda implementação das regras de permissão, paralela à da API, e toda
divergência entre as duas seria vazamento. Um teste que só conferisse "publicou"
deixaria essa porta aberta para a primeira pessoa que achasse prático mandar o
nome da tarefa junto.
"""

import json
from unittest.mock import patch

import pytest

from plane.utils import tempo_real
from plane.utils.tempo_real import CANAL, publicar_mudanca


@pytest.fixture
def redis_falso():
    """Troca a conexão por um espião e a devolve zerada depois.

    O `_cliente` é global por processo — sem restaurá-lo, um teste contaminaria
    o seguinte com o espião deste.
    """
    publicadas = []

    class Espiao:
        def publish(self, canal, mensagem):
            publicadas.append((canal, mensagem))

    anterior = tempo_real._cliente
    tempo_real._cliente = Espiao()
    try:
        yield publicadas
    finally:
        tempo_real._cliente = anterior


def carga(publicadas, indice=0):
    return json.loads(publicadas[indice][1])


@pytest.mark.contract
class TestOQueOAvisoCarrega:
    def test_publica_no_canal_combinado(self, redis_falso):
        """O nome do canal é contrato com o `live`; mudar de um lado só o desliga."""
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")

        assert len(redis_falso) == 1
        assert redis_falso[0][0] == CANAL

    def test_leva_identificadores_e_o_tipo(self, redis_falso):
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")

        assert carga(redis_falso) == {
            "tipo": "alterada",
            "projeto": "projeto-1",
            "tarefa": "tarefa-1",
            "ator": "pessoa-1",
        }

    def test_nao_leva_conteudo_nenhum(self, redis_falso):
        """A afirmação que sustenta o desenho inteiro — ver o cabeçalho.

        Escrito como lista fechada de chaves, e não como "não contém `name`":
        assim, quem acrescentar um campo novo ao aviso tem de passar por aqui e
        decidir de propósito, em vez de descobrir depois que vazou.
        """
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")

        assert set(carga(redis_falso)) == {"tipo", "projeto", "tarefa", "ator"}

    def test_ator_ausente_vira_nulo(self, redis_falso):
        """Sem ator, o cliente não tem como reconhecer o próprio eco — e tudo bem.

        O que não pode é a chave sumir: o cliente lê `dados.ator` sem guarda.
        """
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", None)

        assert carga(redis_falso)["ator"] is None


@pytest.mark.contract
class TestOQueNaoViraAviso:
    """Publicar o que ninguém consome é ruído que parece funcionalidade."""

    @pytest.mark.parametrize(
        "tipo",
        [
            "issue.activity.created",  # Fase 2: muda a participação na lista
            "issue.activity.deleted",  # Fase 2
            "issue_draft.activity.updated",  # rascunho não é cartão de ninguém
            "issue_reaction.activity.created",  # não aparece no cartão
            "attachment.activity.created",
        ],
    )
    def test_tipo_fora_da_fase_1_nao_publica(self, redis_falso, tipo):
        publicar_mudanca(tipo, "tarefa-1", "projeto-1", "pessoa-1")

        assert redis_falso == []

    @pytest.mark.parametrize(
        "issue_id,project_id",
        [(None, "projeto-1"), ("tarefa-1", None), (None, None)],
    )
    def test_sem_identificador_nao_publica(self, redis_falso, issue_id, project_id):
        """Aviso sem alvo não teria como ser entregue, e o `live` o descartaria."""
        publicar_mudanca("issue.activity.updated", issue_id, project_id, "pessoa-1")

        assert redis_falso == []


@pytest.mark.contract
class TestCicloEModuloContamComoAlteracao:
    """No quadro do projeto, ciclo e módulo são campos do cartão como outro qualquer."""

    @pytest.mark.parametrize(
        "tipo",
        [
            "cycle.activity.created",
            "cycle.activity.deleted",
            "module.activity.created",
            "module.activity.deleted",
        ],
    )
    def test_publica_como_alterada(self, redis_falso, tipo):
        publicar_mudanca(tipo, "tarefa-1", "projeto-1", "pessoa-1")

        assert len(redis_falso) == 1
        assert carga(redis_falso)["tipo"] == "alterada"


@pytest.mark.contract
class TestFalhaNaoDerrubaOHistorico:
    """A razão de o aviso ser silencioso.

    Ele roda no funil de `issue_activity`, logo depois de o histórico ser
    gravado. Redis fora do ar não pode transformar "arrastei um cartão" em erro:
    sem aviso, a tela volta a se comportar como antes — desatualizada, e não
    quebrada.
    """

    def test_redis_quebrado_nao_levanta(self):
        class Quebrado:
            def publish(self, canal, mensagem):
                raise ConnectionError("redis fora do ar")

        anterior = tempo_real._cliente
        tempo_real._cliente = Quebrado()
        try:
            with patch("plane.utils.tempo_real.log_exception") as registrou:
                publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")
            assert registrou.called, "engolir o erro sem registrar esconderia a falha"
        finally:
            tempo_real._cliente = anterior

    def test_conexao_quebrada_e_solta_para_a_proxima_tentar_de_novo(self):
        """Sem soltar, um cliente inutilizável repetiria o erro para sempre."""

        class Quebrado:
            def publish(self, canal, mensagem):
                raise ConnectionError("redis fora do ar")

        anterior = tempo_real._cliente
        tempo_real._cliente = Quebrado()
        try:
            with patch("plane.utils.tempo_real.log_exception"):
                publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")
            assert tempo_real._cliente is None
        finally:
            tempo_real._cliente = anterior
