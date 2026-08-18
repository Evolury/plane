# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Avisa o `live` de que uma tarefa mudou (ADR 0013).

O produto não tinha como dizer ao cliente "mudou algo que não foi você": o
quadro atualiza o cartão otimisticamente, do que ELE mesmo mandou, e não revalida
nem ao voltar para a aba. Automação, que muda a tarefa no Celery depois da
resposta HTTP, era a primeira funcionalidade a expor isso — o responsável só
aparecia depois de recarregar a página.

**O evento carrega identificadores, nunca conteúdo.** É a decisão que define o
risco desta funcionalidade: mandar o dado da tarefa obrigaria o servidor a
decidir, por destinatário, quem pode ver cada campo — uma segunda implementação
das regras de permissão, paralela à da API, e toda divergência entre as duas
seria vazamento. Mandando só o aviso, quem recebe vai buscar a tarefa pela API
normal, que já aplica todas as regras: quem não pode ver leva 404 e não mostra
nada.

Este módulo é caminho quente — roda em toda edição de toda tarefa — e por isso:

* **não levanta exceção.** Redis fora do ar não pode derrubar o registro de
  histórico de quem estava só arrastando um cartão. Sem aviso, a tela volta a se
  comportar como antes: desatualizada, não quebrada.
* **reaproveita a conexão.** `redis_instance()` monta um pool novo a cada
  chamada, o que é aceitável nos usos esporádicos que já existem e não seria
  aqui.
"""

import json

from plane.settings.redis import redis_instance
from plane.utils.exception_logger import log_exception

#: O canal em que o `live` escuta. Um só: quem filtra por projeto é o `live`,
#: que já tem as conexões abertas na mão e sabe quem está olhando o quê. Um
#: canal por projeto multiplicaria assinaturas no Redis sem economizar nada.
CANAL = "evolury:tarefas"

#: Tipo de atividade → o que dizer ao cliente.
#:
#: Só "alterada" por enquanto (Fase 1 do ADR 0013): é o que resolve as seis
#: ações de campo, o defeito relatado entre elas. "criada" e "removida" mudam a
#: PARTICIPAÇÃO da tarefa na lista, e o cliente precisa de tratamento próprio
#: para elas — acrescentar aqui antes disso seria emitir evento que ninguém
#: consome.
#:
#: Ciclo e módulo entram como alteração porque, no quadro do projeto, são campos
#: do cartão como qualquer outro. Que eles também mudem a participação nos
#: quadros de ciclo e de módulo é assunto da Fase 2.
TIPO_DE_EVENTO = {
    "issue.activity.updated": "alterada",
    "cycle.activity.created": "alterada",
    "cycle.activity.deleted": "alterada",
    "module.activity.created": "alterada",
    "module.activity.deleted": "alterada",
}

_cliente = None


def _conexao():
    """Uma conexão por processo, criada na primeira publicação."""
    global _cliente
    if _cliente is None:
        _cliente = redis_instance()
    return _cliente


def publicar_mudanca(tipo, issue_id, project_id, actor_id=None):
    """Publica o aviso. Silenciosa por contrato — ver o cabeçalho do módulo.

    `ator` vai junto para o cliente poder ignorar o próprio eco: quem fez a
    mudança já a aplicou otimisticamente, e rebuscar por causa dela seria
    desfazer a resposta imediata que ele acabou de ver.
    """
    evento = TIPO_DE_EVENTO.get(tipo)
    if evento is None or not issue_id or not project_id:
        return

    try:
        _conexao().publish(
            CANAL,
            json.dumps(
                {
                    "tipo": evento,
                    "projeto": str(project_id),
                    "tarefa": str(issue_id),
                    "ator": str(actor_id) if actor_id else None,
                }
            ),
        )
    except Exception as erro:
        # Uma conexão que morreu fica morta para sempre se ninguém a soltar: o
        # `redis-py` reconecta dentro do pool, mas se o próprio cliente ficou
        # inutilizável (troca de endereço, pool fechado) a próxima publicação
        # repetiria o erro. Soltando aqui, a seguinte monta um cliente novo.
        global _cliente
        _cliente = None
        log_exception(erro)
