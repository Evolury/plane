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
    ICONE_PADRAO_POR_TIPO,
    TIPOS_DE_SELECAO,
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

    # O filtro de exclusão lógica da PROPRIEDADE é explícito porque a junção
    # não passa pelo gerente do modelo — e porque a cascata que apaga os
    # valores roda em tarefa assíncrona. Entre o clique e a tarefa, e para
    # sempre se ela falhar, o valor de um campo excluído continuaria saindo na
    # API e no webhook como um id que não resolve para nada.
    linhas = IssuePropertyValue.objects.filter(issue_id__in=issue_ids, issue_property__deleted_at__isnull=True)
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
            atual[str(propriedade.id)] = _numero_para_api(propriedade, linha.value_number)
        else:
            atual[str(propriedade.id)] = linha.value_text
    return por_tarefa


def icone_efetivo(propriedade):
    """O ícone que a propriedade veste de fato.

    Vazio no banco quer dizer "o padrão do tipo", e a regra mora aqui — num
    lugar só — para a tela, a API pública e o webhook desenharem o mesmo.
    """
    return propriedade.icon or ICONE_PADRAO_POR_TIPO.get(propriedade.property_type, "tag")


def definicoes_das_propriedades(property_ids):
    """As DEFINIÇÕES dos campos pedidos, em uma consulta.

    O valor sozinho não se explica: `{"<uuid>": "<uuid>"}` é um par de ids
    opacos para quem recebe. Quem integra precisa do nome do campo, do tipo, e
    — nas de seleção — do rótulo da opção, senão tem de adivinhar ou fazer uma
    segunda chamada que nem sempre é possível (webhook não faz).

    A ordem é a mesma da tela: `sort_order` e, no empate, a criação.
    """
    if not property_ids:
        return []

    propriedades = (
        IssueProperty.objects.filter(id__in=list(property_ids))
        .prefetch_related("options")
        .order_by("sort_order", "created_at")
    )

    definicoes = []
    for propriedade in propriedades:
        definicao = {
            "id": str(propriedade.id),
            "name": propriedade.name,
            "property_type": propriedade.property_type,
            "is_required": propriedade.is_required,
            "is_active": propriedade.is_active,
            "currency": propriedade.currency,
            "decimal_places": propriedade.decimal_places,
            "icon": icone_efetivo(propriedade),
        }
        if propriedade.property_type in TIPOS_DE_SELECAO:
            # Só as de seleção levam opções. Nas demais a chave seria uma lista
            # vazia em todo payload — ruído que quem lê teria de aprender a
            # ignorar.
            definicao["options"] = [
                {"id": str(opcao.id), "name": opcao.name, "color": opcao.color}
                for opcao in sorted(propriedade.options.all(), key=lambda o: (o.sort_order, o.created_at))
            ]
        definicoes.append(definicao)
    return definicoes


def _numero_para_api(propriedade, numero):
    """O número no formato que a configuração pediu.

    `DecimalField` guarda com a precisão da COLUNA — seis casas —, então
    `str()` de um valor de 2 casas devolve "50.000000". A configuração era
    respeitada ao gravar e ignorada ao ler, e o campo mostrava um número que
    ninguém escolheu.

    Moeda é recortada nas casas configuradas; número perde os zeros à direita,
    porque ali a precisão é de quem digita e não da coluna.
    """
    if numero is None:
        return None
    if propriedade.property_type == PropertyType.CURRENCY:
        casas = propriedade.decimal_places or 0
        return str(numero.quantize(Decimal(1).scaleb(-casas)))
    # `format(..., "f")` porque `normalize()` sozinho devolve notação
    # científica em número redondo: Decimal("100").normalize() é 1E+2.
    return format(numero.normalize(), "f")


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
            numero = Decimal(str(valor))
        except (InvalidOperation, ValueError) as erro:
            raise ValorInvalido(f"{propriedade.name}: número inválido.") from erro

        # A precisão é RECUSADA, não arredondada. Arredondar dinheiro em
        # silêncio troca o número que a pessoa digitou por outro, e ela só
        # descobre no relatório — enquanto recusar acontece na frente dela,
        # com o campo ainda aberto.
        casas = propriedade.decimal_places if propriedade.property_type == PropertyType.CURRENCY else CASAS_DO_BANCO
        expoente = -numero.as_tuple().exponent
        if expoente > casas:
            raise ValorInvalido(f"{propriedade.name}: use no máximo {casas} casa(s) decimal(is).")
        return {"value_number": numero}

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

    # Converter ANTES de apagar. Na ordem inversa, um valor recusado destruía o
    # que já estava gravado: a pessoa perdia o número novo E o antigo, e o erro
    # dizia "use no máximo 2 casas" sobre um campo que tinha acabado de esvaziar.
    campos = _converter(propriedade, valor)
    antigas.delete()
    IssuePropertyValue.objects.create(**comuns, **campos)


def validar_valores(project_id, valores):
    """Confere os valores SEM gravar, e levanta `ValorInvalido` no primeiro erro.

    Existe porque a criação da tarefa grava os valores depois de salvar a
    tarefa: sem esta passagem antes, um valor recusado deixaria a tarefa criada
    e devolveria erro — e quem tentasse de novo criaria a segunda.
    """
    if not valores:
        return
    por_id = {str(p.id): p for p in propriedades_ativas(project_id)}
    for propriedade_id, valor in valores.items():
        propriedade = por_id.get(str(propriedade_id))
        if propriedade is None or esta_vazio(valor):
            continue
        if propriedade.property_type in TIPOS_DE_SELECAO:
            _opcoes_validas(propriedade, valor if isinstance(valor, (list, tuple)) else [valor])
        else:
            _converter(propriedade, valor)


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

#: Casas decimais que a coluna do banco guarda. Acima disso o Postgres
#: arredondaria sozinho, e arredondamento silencioso é o que este módulo evita.
CASAS_DO_BANCO = 6


#: Os operadores que cada tipo aceita — a mesma tabela dos dois caminhos.
#:
#: `in` para seleção e texto, faixa para número, moeda e data. Nada além
#: disso: operador que a especificação não declarou não vira consulta.
OPERADORES_POR_TIPO = {
    PropertyType.SELECT: ("in",),
    PropertyType.MULTI_SELECT: ("in",),
    PropertyType.TEXT: ("in",),
    PropertyType.NUMBER: ("gte", "lte"),
    PropertyType.CURRENCY: ("gte", "lte"),
    PropertyType.DATE: ("gte", "lte"),
}


def q_de_propriedade(propriedade, operadores):
    """A condição de UMA propriedade, como subconsulta.

    Subconsulta, e não join, por duas razões:

    1. **Composição.** Os filtros ricos montam uma árvore de `and`/`or`/`not`
       e a aplicam num `.filter()` só. Duas condições de join no mesmo
       `.filter()` recaem sobre a MESMA linha da tabela de valores — "canal =
       indicação E tag = urgente" devolveria vazio para uma tarefa que tem as
       duas. A subconsulta não tem esse problema: cada uma é uma pergunta
       fechada sobre o conjunto de tarefas.
    2. **Exclusão lógica.** O join por `property_values__…` não passa pelo
       gerente do modelo, então valor apagado continuaria pesando. Aqui o
       `deleted_at__isnull=True` está escrito.

    Devolve `None` quando não sobrou nada válido para perguntar — pedido
    malformado não vira consulta, nem silenciosamente ampla, nem erro de ORM.
    """
    import uuid as _uuid

    from django.db.models import Q

    linhas = IssuePropertyValue.objects.filter(issue_property_id=propriedade.id, deleted_at__isnull=True)

    if propriedade.property_type in TIPOS_DE_SELECAO:
        validas = []
        for escolhida in _lista(operadores.get("in")):
            try:
                _uuid.UUID(escolhida)
                validas.append(escolhida)
            except (ValueError, AttributeError, TypeError):
                continue
        if not validas:
            return None
        linhas = linhas.filter(value_option_id__in=validas)

    elif propriedade.property_type == PropertyType.TEXT:
        trecho = operadores.get("in")
        trecho = trecho[0] if isinstance(trecho, (list, tuple)) else trecho
        if not trecho:
            return None
        linhas = linhas.filter(value_text__icontains=str(trecho))

    else:
        coluna = "value_date" if propriedade.property_type == PropertyType.DATE else "value_number"
        tem = False
        for operador in ("gte", "lte"):
            bruto = operadores.get(operador)
            bruto = bruto[0] if isinstance(bruto, (list, tuple)) else bruto
            if bruto in (None, ""):
                continue
            try:
                convertido = (
                    parse_date(str(bruto)) if propriedade.property_type == PropertyType.DATE else Decimal(str(bruto))
                )
            except (InvalidOperation, ValueError):
                continue
            if convertido is None:
                continue
            linhas = linhas.filter(**{f"{coluna}__{operador}": convertido})
            tem = True
        if not tem:
            return None

    return Q(pk__in=linhas.values("issue_id"))


def _lista(bruto):
    """Aceita `"a,b"` e `["a", "b"]` — os dois caminhos chegam aqui."""
    if bruto in (None, ""):
        return []
    if isinstance(bruto, (list, tuple)):
        return [str(v) for v in bruto if v]
    return [v for v in str(bruto).split(",") if v]


def propriedades_por_id(ids):
    """As propriedades existentes entre os ids pedidos, numa consulta."""
    validos = []
    import uuid as _uuid

    for cru in ids:
        try:
            _uuid.UUID(str(cru))
            validos.append(str(cru))
        except (ValueError, AttributeError, TypeError):
            continue
    if not validos:
        return {}
    return {
        str(p.id): p
        for p in IssueProperty.objects.filter(id__in=validos).only("id", "property_type", "is_active", "project_id")
    }


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

    por_id = propriedades_por_id(pedidos.keys())

    condicoes = []
    for propriedade_id, operadores in pedidos.items():
        propriedade = por_id.get(propriedade_id)
        if propriedade is None:
            continue
        condicao = q_de_propriedade(propriedade, operadores)
        if condicao is not None:
            condicoes.append(condicao)

    return condicoes


def aplicar_filtros_de_propriedade(queryset, query_params):
    """Aplica as condições de propriedade ao conjunto."""
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
