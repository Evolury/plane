# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A chamada ao Live leva a chave de servidor (revisão do upstream, 16/08/2026).

`/convert-document/` passou a exigir `live-server-secret-key`. Esta é a metade
que quebraria **em silêncio**: sem o cabeçalho, o Live responde 401, a tarefa
engole a falha e a duplicação de página perde a descrição — sem erro na tela,
sem alarme em lugar nenhum.

Corresponde ao `GHSA-55gq-rf47-9pqx` do upstream.
"""

from unittest.mock import patch

import pytest
from django.test import override_settings

from plane.bgtasks.copy_s3_object import sync_with_external_service


@pytest.mark.unit
class TestChamadaAoLive:
    @override_settings(LIVE_URL="http://live:3000", LIVE_SERVER_SECRET_KEY="segredo-de-teste")
    def test_manda_a_chave_de_servidor(self):
        with patch("plane.bgtasks.copy_s3_object.requests.post") as chamada:
            chamada.return_value.status_code = 200
            chamada.return_value.json.return_value = {}

            sync_with_external_service("PAGE", "<p>oi</p>")

        assert chamada.called
        cabecalhos = chamada.call_args.kwargs.get("headers") or {}
        assert cabecalhos.get("live-server-secret-key") == "segredo-de-teste"

    @override_settings(LIVE_URL="http://live:3000", LIVE_SERVER_SECRET_KEY="segredo-de-teste")
    def test_a_chamada_tem_tempo_limite(self):
        """Sem limite, um Live pendurado prende o worker indefinidamente."""
        with patch("plane.bgtasks.copy_s3_object.requests.post") as chamada:
            chamada.return_value.status_code = 200
            chamada.return_value.json.return_value = {}

            sync_with_external_service("PAGE", "<p>oi</p>")

        assert chamada.call_args.kwargs.get("timeout")

    @override_settings(LIVE_URL=None, LIVE_SERVER_SECRET_KEY="segredo-de-teste")
    def test_sem_live_configurado_nao_chama(self):
        with patch("plane.bgtasks.copy_s3_object.requests.post") as chamada:
            assert sync_with_external_service("PAGE", "<p>oi</p>") == {}
        assert not chamada.called
