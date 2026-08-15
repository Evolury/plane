# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Leitura e escrita dos valores de propriedade personalizada (ADR 0011, P2).

Tudo aqui é **em bloco por conjunto de tarefas**. Os layouts carregam centenas
de tarefas por página, e nenhuma leitura pode custar consulta por tarefa — é a
consequência que o ADR registrou e que os tetos de consulta desta base cobram.

O formato do valor na API é um por tipo, e o mais simples que cada um permite:

    texto/moeda/número  ->  "algo" | 12.5
    data                ->  "2026-08-20"
    seleção única       ->  "<id da opção>"
    seleção múltipla    ->  ["<id>", "<id>"]

Vazio é sempre `None` (ou lista vazia): apagar o valor é escrever vazio, e não
existe um segundo caminho para isso.
"""

# Python imports
from collections import defaultdict
from decimal import Decimal, InvalidOperation

# Django imports
from django.utils.dateparse import parse_date

# Module imports
from plane.db.models import (
    IssueProperty,
    IssuePropertyOption,
    IssuePropertyValue,
    PropertyType,
)


def propriedades_ativas(project_id):
    """As propriedades que os formulários mostram. Desativada preserva valor e some da tela."""
    return list(
        IssueProperty.objects.filter(project_id=project_id, is_active=True)
        .prefetch_related("options")
        .order_by("sort_order", "created_at")
    )


def valores_por_tarefa(issue_ids, property_ids=None):
    """`{issue_id: {property_id: valor}}`, em uma consulta.

    Devolve o valor já no formato da API — lista nas de seleção múltipla,
    escalar nas demais —, para que quem chama não precise conhecer o modelo.

    `property_ids` recorta o que volta. Sem ele, quem pede os valores do cartão
    receberia também os que o cartão não mostra — resposta maior que a pergunta,
    e dado interno viajando para uma tela que não pediu por ele.
    """
    por_tarefa = defaultdict(dict)
    if not issue_ids:
        return por_tarefa

    linhas = IssuePropertyValue.objects.filter(issue_id__in=issue_ids)
    if property_ids is not None:
        linhas = linhas.filter(issue_property_id__in=property_ids)
    linhas = linhas.select_related("issue_property")
    for linha in linhas:
        propriedade = linha.issue_property
        atual = por_tarefa[linha.issue_id]
        if propriedade.property_type == PropertyType.MULTI_SELECT:
            atual.setdefault(str(propriedade.id), []).append(str(linha.value_option_id))
        elif propriedade.property_type == PropertyType.SELECT:
            atual[str(propriedade.id)] = str(linha.value_option_id) if linha.value_option_id else None
        elif propriedade.property_type == PropertyType.DATE:
            atual[str(propriedade.id)] = linha.value_date.isoformat() if linha.value_date else None
        elif propriedade.property_type in (PropertyType.NUMBER, PropertyType.CURRENCY):
            atual[str(propriedade.id)] = str(linha.value_number) if linha.value_number is not None else None
        else:
            atual[str(propriedade.id)] = linha.value_text
    return por_tarefa


def esta_vazio(valor):
    if valor is None:
        return True
    if isinstance(valor, (list, tuple, set)):
        return len(valor) == 0
    return str(valor).strip() == ""


def faltando_obrigatorias(project_id, valores):
    """Os nomes das propriedades obrigatórias que o pedido não trouxe.

    Só vale na CRIAÇÃO. Obrigatória nunca barra a conclusão, e nunca alcança
    tarefa que já existia — aplicá-la ao passado transformaria uma configuração
    de hoje em dívida retroativa do projeto inteiro (ADR 0011).
    """
    valores = valores or {}
    faltando = []
    for propriedade in IssueProperty.objects.filter(project_id=project_id, is_active=True, is_required=True):
        if esta_vazio(valores.get(str(propriedade.id))):
            faltando.append(propriedade.name)
    return faltando


class ValorInvalido(ValueError):
    """O valor não cabe no tipo da propriedade."""


def _converter(propriedade, valor):
    """Traduz o valor da API para as colunas tipadas, ou recusa.

    Recusar é o ponto: guardar "abc" numa coluna de número ou um id de opção
    que não é da propriedade transformaria erro de quem chama em dado sujo, e
    dado sujo só aparece semanas depois, na ordenação ou no relatório.
    """
    if propriedade.property_type == PropertyType.DATE:
        data = parse_date(str(valor))
        if data is None:
            raise ValorInvalido(f"{propriedade.name}: data inválida.")
        return {"value_date": data}

    if propriedade.property_type in (PropertyType.NUMBER, PropertyType.CURRENCY):
        try:
            return {"value_number": Decimal(str(valor))}
        except (InvalidOperation, ValueError) as erro:
            raise ValorInvalido(f"{propriedade.name}: número inválido.") from erro

    return {"value_text": str(valor)}


def _opcoes_validas(propriedade, ids):
    """Só as opções DESTA propriedade. Id de outra seria vínculo cruzado silencioso."""
    validas = list(
        IssuePropertyOption.objects.filter(issue_property=propriedade, id__in=ids).values_list("id", flat=True)
    )
    if len(validas) != len(set(str(i) for i in ids)):
        raise ValorInvalido(f"{propriedade.name}: opção inválida.")
    return validas


def gravar_valor(issue, propriedade, valor):
    """Grava (ou apaga) o valor de uma propriedade numa tarefa.

    Apagar é escrever vazio: as linhas antigas saem, e não sobra caminho
    alternativo para "sem valor" que a leitura precisasse conhecer.
    """
    antigas = IssuePropertyValue.objects.filter(issue=issue, issue_property=propriedade)
    if esta_vazio(valor):
        antigas.delete()
        return

    comuns = {
        "issue": issue,
        "issue_property": propriedade,
        "project_id": issue.project_id,
        "workspace_id": issue.workspace_id,
    }

    if propriedade.property_type == PropertyType.MULTI_SELECT:
        escolhidas = _opcoes_validas(propriedade, valor if isinstance(valor, (list, tuple)) else [valor])
        antigas.delete()
        IssuePropertyValue.objects.bulk_create(
            [IssuePropertyValue(**comuns, value_option_id=opcao) for opcao in escolhidas],
            batch_size=100,
            ignore_conflicts=True,
        )
        return

    if propriedade.property_type == PropertyType.SELECT:
        escolhida = _opcoes_validas(propriedade, [valor])[0]
        antigas.delete()
        IssuePropertyValue.objects.create(**comuns, value_option_id=escolhida)
        return

    antigas.delete()
    IssuePropertyValue.objects.create(**comuns, **_converter(propriedade, valor))


def gravar_valores(issue, valores):
    """Grava um conjunto de valores de uma vez — o caminho da criação da tarefa."""
    if not valores:
        return
    por_id = {str(p.id): p for p in propriedades_ativas(issue.project_id)}
    for propriedade_id, valor in valores.items():
        propriedade = por_id.get(str(propriedade_id))
        if propriedade is not None:
            gravar_valor(issue, propriedade, valor)


def rotulo_do_valor(propriedade, valor):
    """O valor como texto legível — é o que a atividade e a exportação mostram.

    Id de opção no histórico não diz nada a quem lê seis meses depois.
    """
    if esta_vazio(valor):
        return ""
    if propriedade.property_type in (PropertyType.SELECT, PropertyType.MULTI_SELECT):
        ids = valor if isinstance(valor, (list, tuple)) else [valor]
        nomes = IssuePropertyOption.objects.filter(issue_property=propriedade, id__in=ids).values_list(
            "name", flat=True
        )
        return ", ".join(nomes)
    if propriedade.property_type == PropertyType.CURRENCY:
        return f"{propriedade.currency} {valor}"
    return str(valor)


#: O prefixo dos parâmetros de filtro por propriedade personalizada.
#:
#: Precisa ser prefixo, e não uma chave fixa como os outros filtros, porque o
#: "campo" aqui é um id que só existe em tempo de execução.
PREFIXO_DE_FILTRO = "property_"


def filtros_de_propriedade(query_params):
    """Traduz `property_<uuid>` em condições, uma por propriedade.

    Devolve uma LISTA de `Q`, e não um dicionário de `kwargs`, por uma razão
    de correção: os filtros do produto viram `kwargs` de uma única chamada de
    `.filter()`, e duas propriedades ali colidiriam no mesmo join — a segunda
    condição recairia sobre a linha que a primeira já escolheu, e o resultado
    seria vazio sem ninguém entender por quê. Cada `Q` é aplicado em sua
    própria chamada, que é o que força um join por propriedade.

    Operadores, um por tipo, e só os que a especificação declarou:

        seleção          property_<id>=opcao,opcao      tem qualquer uma
        texto            property_<id>=trecho           contém
        número/moeda     property_<id>_gte / _lte       faixa
        data             property_<id>_gte / _lte       faixa
    """
    import uuid as _uuid

    from django.db.models import Q

    pedidos = {}
    for chave, valor in query_params.items():
        if not chave.startswith(PREFIXO_DE_FILTRO) or not valor:
            continue
        resto = chave[len(PREFIXO_DE_FILTRO) :]
        operador = "in"
        for sufixo in ("_gte", "_lte"):
            if resto.endswith(sufixo):
                resto, operador = resto[: -len(sufixo)], sufixo[1:]
                break
        try:
            _uuid.UUID(resto)
        except (ValueError, AttributeError, TypeError):
            # Id malformado é pedido de quem chama, e pedido malformado não
            # vira consulta — nem silenciosamente ampla, nem erro de ORM.
            continue
        pedidos.setdefault(resto, {})[operador] = valor

    if not pedidos:
        return []

    por_id = {str(p.id): p for p in IssueProperty.objects.filter(id__in=pedidos.keys()).only("id", "property_type")}

    condicoes = []
    for propriedade_id, operadores in pedidos.items():
        propriedade = por_id.get(propriedade_id)
        if propriedade is None:
            continue
        base = Q(property_values__issue_property_id=propriedade_id)

        if propriedade.property_type in (PropertyType.SELECT, PropertyType.MULTI_SELECT):
            escolhidas = [v for v in (operadores.get("in") or "").split(",") if v]
            validas = []
            for escolhida in escolhidas:
                try:
                    _uuid.UUID(escolhida)
                    validas.append(escolhida)
                except (ValueError, AttributeError, TypeError):
                    continue
            if not validas:
                continue
            condicoes.append(base & Q(property_values__value_option_id__in=validas))
            continue

        if propriedade.property_type == PropertyType.TEXT:
            trecho = operadores.get("in")
            if trecho:
                condicoes.append(base & Q(property_values__value_text__icontains=trecho))
            continue

        coluna = "value_date" if propriedade.property_type == PropertyType.DATE else "value_number"
        faixa = Q()
        tem = False
        for operador, sufixo in (("gte", "__gte"), ("lte", "__lte")):
            bruto = operadores.get(operador)
            if not bruto:
                continue
            try:
                convertido = (
                    parse_date(str(bruto)) if propriedade.property_type == PropertyType.DATE else Decimal(str(bruto))
                )
            except (InvalidOperation, ValueError):
                continue
            if convertido is None:
                continue
            faixa &= Q(**{f"property_values__{coluna}{sufixo}": convertido})
            tem = True
        if tem:
            condicoes.append(base & faixa)

    return condicoes


def aplicar_filtros_de_propriedade(queryset, query_params):
    """Aplica cada condição em SUA chamada de `.filter()`.

    Uma chamada por propriedade é o que garante um join por propriedade —
    juntar tudo num `.filter()` só faria a segunda condição recair sobre a
    linha que a primeira escolheu, e "canal = indicação E tag = urgente"
    devolveria vazio para uma tarefa que tem as duas.
    """
    for condicao in filtros_de_propriedade(query_params):
        queryset = queryset.filter(condicao)
    return queryset


#: Prefixo do `group_by` por propriedade personalizada.
#:
#: Sem `__` no meio de propósito: o alias vira anotação do ORM, e o Django
#: recusa apelido de coluna com `__`. Por isso o id vai em hexadecimal, sem
#: hífens — `property_<hex>`.
PREFIXO_DE_AGRUPAMENTO = "property_"


def alias_de_agrupamento(group_by):
    """O id da propriedade quando `group_by` é `property_<hex>`, senão `None`.

    Como na ordenação, a validação vem antes de qualquer coisa tocar o ORM:
    valor de quem chama não pode virar nome de campo.
    """
    import uuid as _uuid

    if not group_by or not str(group_by).startswith(PREFIXO_DE_AGRUPAMENTO):
        return None
    cru = str(group_by)[len(PREFIXO_DE_AGRUPAMENTO) :]
    try:
        identificador = _uuid.UUID(cru)
    except (ValueError, AttributeError, TypeError):
        return None
    if not IssueProperty.objects.filter(pk=identificador, property_type=PropertyType.SELECT).exists():
        # Só seleção única agrupa. Texto ou moeda produziriam uma coluna por
        # valor distinto, que é ruído e não organização (ADR 0011).
        return None
    return identificador


def anotacao_de_agrupamento(group_by):
    """A anotação que faz o agrupamento funcionar, ou `None`.

    O paginador usa o nome do campo em `F()`, em `values()` e na partição de
    janela — tudo isso resolve anotação, e é por isso que agrupar por
    propriedade cabe no maquinário existente sem reescrevê-lo.
    """
    from django.db.models import OuterRef, Subquery

    identificador = alias_de_agrupamento(group_by)
    if identificador is None:
        return None
    return {
        str(group_by): Subquery(
            IssuePropertyValue.objects.filter(issue=OuterRef("pk"), issue_property_id=identificador).values(
                "value_option_id"
            )[:1]
        )
    }


def valores_de_agrupamento(group_by):
    """As colunas do quadro: as opções, na ordem configurada, mais a vazia.

    `"None"` no fim porque tarefa sem valor precisa de uma coluna onde caber —
    sem ela, agrupar esconderia trabalho, que é o pior que um quadro pode fazer.
    """
    identificador = alias_de_agrupamento(group_by)
    if identificador is None:
        return None
    opcoes = list(
        IssuePropertyOption.objects.filter(issue_property_id=identificador)
        .order_by("sort_order", "created_at")
        .values_list("id", flat=True)
    )
    return opcoes + ["None"]
