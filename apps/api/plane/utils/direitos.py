# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O que cada espaço de trabalho tem direito a fazer — ver ADR 0021.

Duas perguntas, e só duas:

- **`recurso_liberado(espaço, nome)`** — booleano. Tem analytics ou não tem.
- **`limite(espaço, nome)`** — quantidade. Cinco propriedades, duas automações,
  `None` para sem teto.

Direito não é bandeira de lançamento. Bandeira liga e desliga funcionalidade
para todo mundo; direito responde por espaço, a partir do que foi contratado, e
é avaliado **no servidor** a cada ação. A tela esconde o que o plano não inclui,
mas quem recusa é daqui — qualquer cliente pode falar com a API sem passar pelo
front.

O estado da assinatura (`ativa`, `restrita`, …) mora ao lado, mas responde outra
pergunta: direito é *o que* o plano inclui; estado é *se* o espaço pode escrever
agora. Quem cruza os dois é o middleware, não este módulo.

**Cache.** A consulta entra em caminho quente — criar tarefa, convidar, abrir o
espaço. Fica em Redis por cinco minutos e é invalidada de propósito na troca de
plano e no webhook. Cinco minutos é o pior atraso possível entre pagar e voltar
a escrever; menos que isso custaria uma consulta por requisição sem melhorar
nada que o cliente perceba.
"""

from typing import Optional

from django.core.cache import cache

from plane.utils import planos, regua

SEGUNDOS_DE_CACHE = 300

# O que o cache guarda por espaço. Deliberadamente pequeno: cabe numa chave, e
# nenhum campo aqui muda sem passar por `esquecer()`.
CAMPOS = (
    "workspace_id",
    "slug",
    "status",
    "plano",
    "assentos_incluidos",
    "convidados_por_assento",
    "existe_espaco",
)

# Espaço sem linha de assinatura nenhuma. Acontece com espaço criado depois da
# migração 0151 e antes de a contratação existir (E4) — e a resposta certa é
# essa, não uma exceção: quem não contratou não tem plano.
SEM_NADA = {
    "workspace_id": None,
    "slug": "",
    "status": regua.SEM_ASSINATURA,
    "plano": "",
    "assentos_incluidos": 0,
    "convidados_por_assento": 0,
    # Espaço que não existe não é espaço sem plano. Sem esta diferença, um slug
    # digitado errado responderia "seu plano não inclui" em vez de "não existe"
    # — medido: dois testes da API pública passaram a receber 402 no lugar de
    # 404 no primeiro dia desta trava.
    "existe_espaco": False,
}


def _chave_por_slug(slug: str) -> str:
    return f"faturamento:espaco:{slug}"


def _chave_por_id(workspace_id) -> str:
    return f"faturamento:espaco-id:{workspace_id}"


def _do_banco(*, slug=None, workspace_id=None) -> Optional[dict]:
    from plane.db.models import Assinatura

    filtro = {"workspace__slug": slug} if slug else {"workspace_id": workspace_id}
    assinatura = (
        Assinatura.objects.filter(**filtro)
        .values("workspace_id", "workspace__slug", "status", "plano", "assentos_incluidos", "convidados_por_assento")
        .first()
    )
    if assinatura is None:
        return None

    assinatura["slug"] = assinatura.pop("workspace__slug")
    assinatura["existe_espaco"] = True
    return assinatura


def dados(*, slug=None, workspace_id=None) -> dict:
    """O retrato do espaço, do cache ou do banco. Nunca `None`.

    Espaço sem assinatura devolve `SEM_NADA` em vez de levantar: a ausência de
    contrato é um caso previsto, e transformá-la em exceção espalharia `try`
    por todo ponto de checagem.
    """
    if not slug and not workspace_id:
        raise ValueError("É preciso dizer qual espaço: `slug` ou `workspace_id`")

    chave = _chave_por_slug(slug) if slug else _chave_por_id(workspace_id)
    guardado = cache.get(chave)
    if guardado is not None:
        return guardado

    encontrado = _do_banco(slug=slug, workspace_id=workspace_id)
    if encontrado is None:
        encontrado = dict(
            SEM_NADA,
            slug=slug or "",
            workspace_id=workspace_id,
            existe_espaco=_existe(slug, workspace_id),
        )

    # Guardado nas duas chaves: quem chega pelo slug e quem chega pelo id leem o
    # mesmo retrato, e `esquecer()` derruba os dois de uma vez.
    cache.set(_chave_por_slug(encontrado["slug"]), encontrado, SEGUNDOS_DE_CACHE)
    if encontrado["workspace_id"]:
        cache.set(_chave_por_id(encontrado["workspace_id"]), encontrado, SEGUNDOS_DE_CACHE)
    return encontrado


def _existe(slug, workspace_id) -> bool:
    from plane.db.models import Workspace

    filtro = {"slug": slug} if slug else {"pk": workspace_id}
    return Workspace.objects.filter(**filtro).exists()


def existe_espaco(*, slug=None, workspace_id=None) -> bool:
    return dados(slug=slug, workspace_id=workspace_id)["existe_espaco"]


def esquecer(*, slug=None, workspace_id=None) -> None:
    """Derruba o retrato guardado. Chamada na troca de plano e no webhook."""
    if slug:
        guardado = cache.get(_chave_por_slug(slug))
        cache.delete(_chave_por_slug(slug))
        if guardado and guardado.get("workspace_id"):
            cache.delete(_chave_por_id(guardado["workspace_id"]))
    if workspace_id:
        guardado = cache.get(_chave_por_id(workspace_id))
        cache.delete(_chave_por_id(workspace_id))
        if guardado and guardado.get("slug"):
            cache.delete(_chave_por_slug(guardado["slug"]))


def estado(*, slug=None, workspace_id=None) -> str:
    return dados(slug=slug, workspace_id=workspace_id)["status"]


def plano_de(*, slug=None, workspace_id=None) -> str:
    return dados(slug=slug, workspace_id=workspace_id)["plano"]


def recurso_liberado(recurso: str, *, slug=None, workspace_id=None) -> bool:
    """O plano inclui este recurso?

    Sem plano, nada é liberado — e é o certo. "Sem plano libera tudo" é a regra
    que transforma qualquer campo vazio por engano em porta aberta.
    """
    chave = plano_de(slug=slug, workspace_id=workspace_id)
    if not chave:
        return False
    return planos.plano(chave).inclui(recurso)


def limite(nome: str, *, slug=None, workspace_id=None) -> Optional[int]:
    """O teto deste espaço para o limite pedido. `None` é sem teto.

    Sem plano, o teto é **zero**: não pode criar nenhuma. Cuidado com a
    diferença — `None` e `0` são respostas opostas, e trocá-las libera tudo.
    """
    chave = plano_de(slug=slug, workspace_id=workspace_id)
    if not chave:
        return 0
    return planos.plano(chave).teto(nome)


def cota_de_convidados(*, slug=None, workspace_id=None) -> int:
    """Quantos convidados o espaço pode ter — múltiplo dos assentos pagos."""
    retrato = dados(slug=slug, workspace_id=workspace_id)
    return retrato["convidados_por_assento"] * retrato["assentos_incluidos"]


def assentos_contratados(*, slug=None, workspace_id=None) -> int:
    return dados(slug=slug, workspace_id=workspace_id)["assentos_incluidos"]


def uso_de_assentos(workspace_id) -> int:
    """Membros que ocupam assento: administradores e membros, gente de verdade.

    Robô nunca conta — a listagem do god-mode já o exclui desde sempre, e
    contá-lo aqui cobraria do cliente por uma integração dele.
    """
    from plane.db.models import WorkspaceMember

    return WorkspaceMember.objects.filter(
        workspace_id=workspace_id, is_active=True, member__is_bot=False, role__in=[20, 15]
    ).count()


def uso_de_convidados(workspace_id) -> int:
    from plane.db.models import WorkspaceMember

    return WorkspaceMember.objects.filter(
        workspace_id=workspace_id, is_active=True, member__is_bot=False, role=5
    ).count()


def uso_de_automacoes(workspace_id) -> int:
    """Regras **ativas** do espaço inteiro, não do projeto.

    A assinatura é do espaço; contar por projeto deixaria o teto de duas regras
    virar duas por projeto, que é outro produto.
    """
    from plane.db.models import Automation

    return Automation.objects.filter(workspace_id=workspace_id, is_active=True, deleted_at__isnull=True).count()


def recusa_de_recurso(recurso: str, plano_atual: str) -> dict:
    """O corpo da recusa. Diz onde está o que o cliente quis.

    Recusar sem dizer onde encontrar transforma a trava em parede — e parede
    não vende plano nenhum.
    """
    from plane.utils.error_codes import ERROR_CODES

    return {
        "error_code": ERROR_CODES["PLANO_NAO_INCLUI"],
        "error_message": "PLANO_NAO_INCLUI",
        "recurso": recurso,
        "plano_atual": plano_atual,
        "planos_com": list(planos.planos_com(recurso)),
    }


def recusa_de_limite(nome: str, teto: int, plano_atual: str) -> dict:
    """Recusa por quantidade — e diz quais planos têm mais."""
    if nome not in planos.LIMITES:
        raise ValueError(f"Limite desconhecido: {nome!r}. Conhecidos: {', '.join(planos.LIMITES)}")
    maiores = [chave for chave in planos.ORDEM if _teto_maior(chave, nome, teto)]
    return _corpo_de_limite(nome, teto, plano_atual, maiores)


def recusa_de_cota_de_convidados(cota: int, plano_atual: str) -> dict:
    """Convidado não é um limite do catálogo: é múltiplo do assento pago.

    Precisa de recusa própria porque "quais planos têm mais" se responde por
    `convidados_por_assento`, e não por um teto fixo — quem tem mais assento
    tem mais convidado no mesmo plano.
    """
    atual = planos.PLANOS[plano_atual].convidados_por_assento if plano_atual else 0
    maiores = [chave for chave in planos.ORDEM if planos.PLANOS[chave].convidados_por_assento > atual]
    return _corpo_de_limite("convidados", cota, plano_atual, maiores)


def _corpo_de_limite(nome: str, teto: int, plano_atual: str, maiores: list) -> dict:
    from plane.utils.error_codes import ERROR_CODES

    return {
        "error_code": ERROR_CODES["LIMITE_DO_PLANO"],
        "error_message": "LIMITE_DO_PLANO",
        "limite": nome,
        "teto": teto,
        "plano_atual": plano_atual,
        "planos_com_mais": maiores,
    }


def _teto_maior(chave: str, nome: str, teto: int) -> bool:
    outro = planos.plano(chave).teto(nome)
    return outro is None or outro > teto
