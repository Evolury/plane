# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Excluir muitas tarefas é a MESMA exclusão, feita em bloco (ADR 0018).

O endpoint de exclusão em massa existia e não fazia o que a exclusão de uma
tarefa faz: `issues.delete()` num queryset cai em `SoftDeletionQuerySet.delete`,
que só escreve `deleted_at` nas próprias tarefas. A exclusão de UMA cai em
`SoftDeleteModel.delete`, que ainda dispara `soft_delete_related_objects` e leva
junto subtarefas, comentários, anexos, vínculos. Pelo caminho em massa, a
subtarefa ficava viva apontando para um pai excluído.

Aqui a cascata é a mesma, mas **por conjunto de linhas, e não por objeto**: uma
consulta por relação, e não uma por tarefa. Com 300 tarefas selecionadas, o
caminho do upstream faria milhares de idas ao banco dentro da requisição.

**As relações são descobertas, não listadas.** Uma lista escrita à mão já
nasceria errada: das 33 relações reversas de `Issue`, seis são deste fork
(etapas por vencimento, recorrentes, propriedades personalizadas, automações), e
a próxima entra sem que ninguém lembre de vir aqui.

**O instante é a identidade do lote.** Todas as linhas de uma exclusão recebem
exatamente o mesmo `deleted_at`, e é isso — e só isso — que torna o desfazer
possível sem coluna nova: restaurar é limpar `deleted_at` onde ele vale aquele
instante. Precisão de microssegundo no Postgres; dois lotes no mesmo tique não
acontecem, e se acontecessem o desfazer devolveria os dois, que é o desfecho
seguro.

**`SET_NULL` fica como está**, ao contrário do que a cascata do upstream faz.
Ela anula o campo (`IssueSequence.issue`, `AutomationRun.issue`, …) — e anular é
perda de dado que nenhum desfazer traz de volta, coisa de exclusão definitiva,
não de exclusão que pode ser desfeita por 60 dias. Quem aponta para uma tarefa
excluída não a enxerga de qualquer forma: o gerente padrão já filtra.
"""

from collections import defaultdict, deque

#: Teto por requisição. Não é limite de banco — é limite de arrependimento: uma
#: seleção que passa disso é quase sempre um "selecionar tudo" que a pessoa não
#: leu, e vale mais recusar com uma frase clara do que apagar depressa.
TETO_DE_EXCLUSAO_EM_MASSA = 500


def _gerente(modelo):
    """O gerente que enxerga o que já foi excluído.

    `objects` filtra `deleted_at` nula, e por isso não serve nem para achar o
    que restaurar nem para evitar remarcar o que já estava excluído.
    """
    return getattr(modelo, "all_objects", None) or modelo._default_manager


def relacoes_em_cascata(modelo):
    """As relações reversas que somem junto com a linha.

    Só `CASCADE`, e só em modelo com exclusão suave — o mesmo critério da
    cascata do upstream, aplicado ao MODELO em vez de a um objeto.
    """
    for campo in modelo._meta.get_fields():
        if not ((campo.one_to_many or campo.one_to_one) and campo.auto_created and not campo.concrete):
            continue
        if getattr(campo.on_delete, "__name__", "") != "CASCADE":
            continue
        alvo = campo.related_model
        if not hasattr(alvo, "deleted_at"):
            continue
        yield alvo, campo.remote_field.name


def modelos_alcancaveis(raiz):
    """Todo modelo que uma exclusão a partir de `raiz` pode marcar.

    É a mesma travessia de `marcar_excluidas`, feita nas CLASSES: o desfazer
    precisa saber onde procurar, e procurar por instante dispensa carregar id
    nenhum.
    """
    vistos = {raiz}
    fila = deque([raiz])
    while fila:
        modelo = fila.popleft()
        for alvo, _ in relacoes_em_cascata(modelo):
            if alvo in vistos:
                continue
            vistos.add(alvo)
            fila.append(alvo)
    return vistos


def marcar_excluidas(Issue, issue_ids, momento):
    """Marca as tarefas e tudo que cai junto com elas, com o mesmo instante.

    Devolve `{rótulo do modelo: quantas linhas}` — a contagem é o que os testes
    olham para saber que a cascata desceu, em vez de acreditar que desceu.

    A travessia termina sozinha porque só percorre linha ainda não excluída:
    uma vez marcada, ela não é encontrada de novo, e o ciclo natural do
    `IssueRelation` (duas chaves para `Issue`) não vira laço infinito.
    """
    contagem = defaultdict(int)

    ids = list(_gerente(Issue).filter(pk__in=issue_ids, deleted_at__isnull=True).values_list("pk", flat=True))
    if not ids:
        return {}

    _gerente(Issue).filter(pk__in=ids).update(deleted_at=momento)
    contagem[Issue._meta.label] += len(ids)

    fila = deque([(Issue, ids)])
    while fila:
        modelo, ids_do_pai = fila.popleft()
        for alvo, campo in relacoes_em_cascata(modelo):
            filhos = list(
                _gerente(alvo)
                .filter(**{f"{campo}__in": ids_do_pai}, deleted_at__isnull=True)
                .values_list("pk", flat=True)
            )
            if not filhos:
                continue
            _gerente(alvo).filter(pk__in=filhos).update(deleted_at=momento)
            contagem[alvo._meta.label] += len(filhos)
            fila.append((alvo, filhos))

    return dict(contagem)


def restaurar_lote(Issue, momento):
    """Desfaz um lote inteiro: limpa `deleted_at` onde ele vale aquele instante.

    Não recebe ids de propósito. Desfazer é desfazer o LOTE — restaurar o pai e
    deixar as subtarefas excluídas devolveria a tarefa pela metade, que é
    exatamente o estado que este módulo existe para não criar.
    """
    contagem = {}
    for modelo in modelos_alcancaveis(Issue):
        quantas = _gerente(modelo).filter(deleted_at=momento).update(deleted_at=None)
        if quantas:
            contagem[modelo._meta.label] = quantas
    return contagem


def separar_por_permissao(issues, actor_id, e_admin):
    """(pode excluir, não pode) — a mesma regra da exclusão de uma tarefa.

    No singular, o servidor aceita administrador do projeto OU quem criou a
    tarefa. Em massa, o upstream exigia administrador, e o resultado era um
    membro que apaga dez tarefas suas uma a uma e não pode apagar as mesmas dez
    de uma vez. A regra não muda com a quantidade.
    """
    if e_admin:
        return list(issues), []
    permitidas, negadas = [], []
    for issue in issues:
        (permitidas if str(issue.created_by_id) == str(actor_id) else negadas).append(issue)
    return permitidas, negadas
