# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Toda tarefa agendada precisa existir de verdade.

A agenda do Celery cita tarefas **por nome, em texto**. Se o worker não importar
o módulo onde a tarefa mora, o agendador dispara todo dia uma mensagem que o
worker recusa — "Received unregistered task" — e nada acontece. Em silêncio: o
disparo dá certo, a recusa fica num log que ninguém lê, e a rotina simplesmente
não roda.

Foi o que aconteceu com a régua de inadimplência na 1.36.0. Das seis tarefas de
faturamento, cinco estavam registradas porque alguma view as importava sem
querer; a sexta, que ninguém importa, ficou de fora — e ela é justamente a que
move os espaços para somente leitura e bloqueio.

O teste percorre a agenda inteira, e não só o faturamento: o defeito é do
formato do agendamento, não daquele módulo.
"""

import pytest

from plane.celery import app


@pytest.mark.unit
class TestAAgendaDoCelery:
    def test_a_agenda_nao_esta_vazia(self):
        # Guarda contra o modo de falha silencioso: a agenda sumir e o teste
        # passar por não ter o que conferir.
        assert len(app.conf.beat_schedule) >= 10

    def test_toda_tarefa_agendada_esta_registrada(self):
        app.loader.import_default_modules()

        agendadas = {entrada["task"] for entrada in app.conf.beat_schedule.values()}
        faltando = sorted(nome for nome in agendadas if nome not in app.tasks)

        assert faltando == [], (
            "A agenda cita tarefas que o worker não conhece. Elas serão "
            "disparadas e recusadas em silêncio: " + ", ".join(faltando)
        )

    def test_as_tarefas_de_faturamento_estao_todas_la(self):
        app.loader.import_default_modules()

        esperadas = [
            "plane.bgtasks.faturamento_conciliacao.alarme_de_silencio_do_asaas",
            "plane.bgtasks.faturamento_conciliacao.conciliar_assinaturas",
            "plane.bgtasks.faturamento_evento.processar_evento_do_asaas",
            "plane.bgtasks.faturamento_excedente.ajustar_excedentes",
            "plane.bgtasks.faturamento_promocao.encerrar_promocoes",
            "plane.bgtasks.faturamento_regua.avancar_regua",
        ]

        assert [nome for nome in esperadas if nome not in app.tasks] == []
