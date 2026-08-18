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
#: Três palavras, e a diferença entre elas é o que o cliente faz ao ouvir:
#:
#: * **alterada** — remendo cirúrgico de uma tarefa que já está no quadro;
#: * **criada**   — rebusca da LISTA, porque o cliente não tem como avaliar os
#:   filtros ricos do quadro sozinho e acrescentar às cegas faria aparecer, para
#:   quem filtrou, um cartão que o filtro exclui;
#: * **removida** — tira do quadro, o que não depende de filtro nenhum.
#:
#: Ciclo e módulo entram como alteração porque, no quadro do projeto, são campos
#: do cartão como qualquer outro.
TIPO_DE_EVENTO = {
    "issue.activity.created": "criada",
    "issue.activity.deleted": "removida",
    "issue.activity.updated": "alterada",
    "cycle.activity.created": "alterada",
    "cycle.activity.deleted": "alterada",
    "module.activity.created": "alterada",
    "module.activity.deleted": "alterada",
}

#: O campo que faz uma tarefa entrar ou sair do quadro sem ser criada nem
#: excluída. Arquivar é `issue.activity.updated` como qualquer edição — só o
#: campo denuncia —, e do ponto de vista de quem olha o quadro o cartão SOME.
CAMPO_DE_ARQUIVAMENTO = "archived_at"

#: O `new_value` que o produto grava ao desarquivar. A tarefa volta ao quadro, e
#: voltar é entrar: mesma resposta que uma criação.
DESARQUIVAR = "restore"

_cliente = None


def _conexao():
    """Uma conexão por processo, criada na primeira publicação."""
    global _cliente
    if _cliente is None:
        _cliente = redis_instance()
    return _cliente


def publicar_propriedade(issue_id, project_id, actor_id=None):
    """Avisa que o VALOR de uma propriedade personalizada mudou.

    Tem função própria, e não um tipo a mais no mapa acima, porque não vem do
    mesmo lugar: a gravação de valor escreve `IssueActivity` direto, sem passar
    pelo funil de `issue_activity`. Era a lacuna que fazia propriedade marcada
    para o cartão continuar exigindo recarga.

    O aviso é separado porque a resposta do cliente também é: o valor não vive
    no store de tarefas, e sim numa chave própria, do projeto inteiro. Rebuscar
    a tarefa não o traria — foi exatamente o defeito do #144, agora entre
    clientes diferentes em vez de dentro do mesmo.
    """
    if not issue_id or not project_id:
        return
    _publicar(
        {
            "tipo": "propriedade",
            "projeto": str(project_id),
            "tarefa": str(issue_id),
            "ator": str(actor_id) if actor_id else None,
        }
    )


def publicar_notificacao(user_ids):
    """Avisa que chegou notificação para estas pessoas.

    Não tem projeto: a caixa de entrada é do workspace, e o sino aparece em
    página que não tem quadro nenhum. Por isso o `live` roteia este aviso pela
    SALA DA PESSOA, e não pela do projeto.

    Vai uma mensagem só, com a lista, e não uma por destinatário: uma tarefa com
    muitos inscritos geraria dezenas de publicações para dizer a mesma coisa.
    Quem separa por pessoa é o `live`, que já tem as conexões na mão.

    O que chega ao navegador NÃO leva a lista: o `live` entrega
    `{"tipo": "notificacao"}` a quem é da sala, e mais nada. Saber quem mais foi
    avisado não é assunto de quem recebe.
    """
    destinatarios = [str(u) for u in (user_ids or []) if u]
    if not destinatarios:
        return
    _publicar({"tipo": "notificacao", "usuarios": destinatarios})


def _evento_do_arquivamento(linhas):
    """Se alguma linha mexeu em `archived_at`, devolve o que dizer; senão, None."""
    for linha in linhas or []:
        if getattr(linha, "field", None) != CAMPO_DE_ARQUIVAMENTO:
            continue
        return "criada" if getattr(linha, "new_value", None) == DESARQUIVAR else "removida"
    return None


def publicar_mudanca(tipo, issue_id, project_id, actor_id=None, linhas=None):
    """Publica o aviso. Silenciosa por contrato — ver o cabeçalho do módulo.

    `ator` vai junto para o cliente poder ignorar o próprio eco: quem fez a
    mudança já a aplicou otimisticamente, e rebuscar por causa dela seria
    desfazer a resposta imediata que ele acabou de ver.

    `linhas` são as de histórico recém-gravadas. Elas entram porque o TIPO
    sozinho não distingue arquivar de editar — as duas chegam como
    `issue.activity.updated`, e só o campo denuncia.
    """
    evento = TIPO_DE_EVENTO.get(tipo)
    if evento is None or not issue_id or not project_id:
        return

    if evento == "alterada":
        evento = _evento_do_arquivamento(linhas) or evento

    _publicar(
        {
            "tipo": evento,
            "projeto": str(project_id),
            "tarefa": str(issue_id),
            "ator": str(actor_id) if actor_id else None,
        }
    )


def _publicar(carga):
    """O envio, com a política de silêncio — ver o cabeçalho do módulo."""
    try:
        _conexao().publish(CANAL, json.dumps(carga))
    except Exception as erro:
        # Uma conexão que morreu fica morta para sempre se ninguém a soltar: o
        # `redis-py` reconecta dentro do pool, mas se o próprio cliente ficou
        # inutilizável (troca de endereço, pool fechado) a próxima publicação
        # repetiria o erro. Soltando aqui, a seguinte monta um cliente novo.
        global _cliente
        _cliente = None
        log_exception(erro)
