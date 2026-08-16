# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O "quando" da automação (ADR 0012).

Traduz o que a linha de atividade grava para o vocabulário que a tela usa — que
é o vocabulário do FILTRO, e não o do histórico. Os dois divergem por motivo
legítimo: o histórico escreve para gente ler ("state", "assignees"), o filtro
escreve para consultar ("state_id", "assignee_id"). A regra é montada com o
segundo, porque é o mesmo seletor de campo do "se"; a tradução mora aqui, num
lugar só.

O que uma mudança carrega, depois de traduzida:

    {"campo": "state_id", "de": "<id ou valor>", "para": "<id ou valor>"}

"de" e "para" são ID quando o campo aponta para outra tabela (estado, pessoa,
etiqueta) e VALOR quando não aponta (prioridade, datas, propriedade). É a mesma
distinção que a linha de atividade já faz entre `old_identifier` e `old_value`,
e é a que o seletor da tela precisa: escolher um estado é escolher um id.
"""

# Module imports
from plane.db.models import AutomationTrigger
from plane.utils.issue_properties import PREFIXO_DE_FILTRO

#: Campo do histórico → campo do filtro.
#:
#: Só entram os campos que a tela oferece como gatilho. Os que ficaram de fora
#: (nome, descrição, pai, estimativa, anexo, link, reação, voto) não estão aqui
#: de propósito: gatilho que ninguém pediu é superfície de laço de graça.
CAMPO_DO_HISTORICO = {
    "state": "state_id",
    "priority": "priority",
    "assignees": "assignee_id",
    "labels": "label_id",
    "start_date": "start_date",
    "target_date": "target_date",
    "modules": "module_id",
    "cycles": "cycle_id",
}

#: Campos cujo "de"/"para" é um id, e não o texto que o histórico mostra.
#:
#: O histórico grava o NOME do estado em `new_value` e o id em `new_identifier`
#: — casar pelo nome funcionaria até alguém renomear a coluna do quadro, e aí a
#: regra pararia em silêncio. Silêncio é o pior defeito possível aqui.
CAMPOS_POR_ID = {"state_id", "assignee_id", "label_id", "module_id", "cycle_id"}

#: Teto de encadeamento entre regras distintas.
#:
#: Existe porque uma regra PODE responder ao que outra fez — é o caso legítimo
#: "mudou para Homologação → prioridade alta" seguido de "prioridade alta →
#: avisar". O que não pode é isso não ter fim. Três é fundo de poço largo o
#: bastante para o encadeamento útil e curto o bastante para o estrago ser
#: pequeno se alguém montar um ciclo.
TETO_DE_PROFUNDIDADE = 3

#: Os gatilhos que respondem a evento — os que o despacho acorda.
#:
#: Mora aqui, e não na tarefa Celery que os usa, porque quem também precisa da
#: lista é o despacho: a agendada nunca entra por evento, quem a chama é o
#: relógio.
GATILHOS_DE_EVENTO = [
    AutomationTrigger.WORK_ITEM_CREATED,
    AutomationTrigger.FIELD_CHANGED,
    AutomationTrigger.COMMENT_ADDED,
]

#: Os gatilhos que a tela pode gravar. Um gatilho fora desta lista seria uma
#: regra que nunca roda, e regra muda é o defeito que este recurso mais precisa
#: evitar — por isso a recusa é na hora de salvar, não na hora de executar.
GATILHOS_ACEITOS = [*GATILHOS_DE_EVENTO, AutomationTrigger.SCHEDULED]


def _valor_da_ponta(linha, ponta):
    """O "de"/"para" de uma linha de atividade, id ou valor conforme o campo."""
    campo = CAMPO_DO_HISTORICO.get(linha.get("field"))
    if campo in CAMPOS_POR_ID:
        bruto = linha.get(f"{ponta}_identifier")
    else:
        bruto = linha.get(f"{ponta}_value")
    if bruto in (None, ""):
        return None
    return str(bruto)


def mudancas_das_atividades(linhas):
    """As linhas de atividade viram a lista de mudanças que a regra entende.

    Uma edição que mexe em três campos produz três linhas e, portanto, três
    mudanças — e uma regra por campo pode casar com cada uma. É o comportamento
    certo: quem trocou estado e responsável de uma vez fez duas coisas.
    """
    mudancas = []
    for linha in linhas:
        if linha.get("verb") != "updated":
            continue
        campo = CAMPO_DO_HISTORICO.get(linha.get("field"))
        if campo is None:
            continue
        mudancas.append(
            {
                "campo": campo,
                "de": _valor_da_ponta(linha, "old"),
                "para": _valor_da_ponta(linha, "new"),
            }
        )
    return mudancas


def mudanca_de_propriedade(propriedade_id, de, para):
    """A mudança de valor de uma propriedade personalizada.

    Vem por fora de `mudancas_das_atividades` porque a linha de atividade
    daquele caminho grava o NOME da propriedade no campo `field` — bom para
    quem lê o histórico, imprestável para casar regra: renomear a propriedade
    quebraria toda regra que a usa, sem aviso. A chave estável é o id, a mesma
    que o filtro já usa (`property_<uuid>`).
    """
    return {
        "campo": f"{PREFIXO_DE_FILTRO}{propriedade_id}",
        "de": None if de in (None, "") else str(de),
        "para": None if para in (None, "") else str(para),
    }


def _qualificador_casa(configurado, valor):
    """A ponta "de X" / "para Y" do gatilho.

    Lista vazia ou ausente quer dizer "qualquer" — é o padrão, e é o que faz
    "quando o estado mudar" funcionar sem obrigar ninguém a escolher destino.
    """
    if not configurado:
        return True
    return valor is not None and str(valor) in {str(item) for item in configurado}


def automacao_casa(automacao, evento) -> bool:
    """A regra responde a este evento?

    `evento` é o dicionário montado pelo despacho: tipo, mudanças, e a origem
    do encadeamento.
    """
    # Uma regra não responde ao que ela mesma fez. Sem isto, "quando a
    # prioridade mudar → mudar a prioridade" seria um laço de um elo só, e o
    # teto de profundidade só o cortaria três voltas depois.
    if evento.get("automacao_origem") and str(evento["automacao_origem"]) == str(automacao.id):
        return False

    gatilho = automacao.trigger_type

    if gatilho == AutomationTrigger.WORK_ITEM_CREATED:
        return evento.get("tipo") == "criada"

    if gatilho == AutomationTrigger.COMMENT_ADDED:
        return evento.get("tipo") == "comentada"

    if gatilho == AutomationTrigger.FIELD_CHANGED:
        if evento.get("tipo") != "alterada":
            return False
        config = automacao.trigger_config or {}
        campo = config.get("field")
        for mudanca in evento.get("mudancas", []):
            if mudanca["campo"] != campo:
                continue
            if not _qualificador_casa(config.get("from"), mudanca["de"]):
                continue
            if not _qualificador_casa(config.get("to"), mudanca["para"]):
                continue
            return True
        return False

    # Agendada não é acordada por evento: quem a chama é o relógio.
    return False
