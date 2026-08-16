# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: o usuário-robô que assina as ações da automação (ADR 0012).
#
# Existe por honestidade de rastro. Hoje o auto-arquivamento credita as
# mudanças a `project.created_by_id` — a pessoa que criou o projeto aparece no
# histórico tendo arquivado tarefas que nunca viu. Com ator próprio, a linha do
# tempo diz o que aconteceu de verdade, e quem lê consegue separar o que uma
# pessoa fez do que uma regra fez.
#
# O robô NÃO é a trava de laço. Chegamos a considerar ignorar todo evento
# assinado por ele, o que tornaria o laço impossível — e tornaria impossível
# junto o encadeamento legítimo ("mudou para Homologação → prioridade alta",
# seguido de "prioridade alta → avisar"). As travas são outras três, e estão em
# `gatilhos.py` e `automation_task.py`: teto de profundidade, regra que não
# responde a si mesma, e teto de execuções por hora. Some-se a elas o descarte
# de ação sem efeito, que é o que faz um ciclo convergir na prática — na
# segunda volta o valor já é o esperado, nada é gravado, e nenhum evento nasce.
#
# É um robô por workspace, e não um por instalação, porque o nome aparece na
# tela de quem lê o histórico — e workspace é a fronteira do que essa pessoa vê.

# Django imports
from django.db import IntegrityError, transaction

# Module imports
from plane.db.models import User

BOT_TYPE = "automation"
NOME_DE_EXIBICAO = "Automação"
# Domínio reservado, não roteável: o robô não recebe e-mail e não faz login.
# `.invalid` é reservado pela RFC 2606 justamente para isto, então nenhum
# endereço real pode colidir.
DOMINIO = "automacao.invalid"


def _email_do_robo(workspace_id) -> str:
    return f"automacao-{workspace_id}@{DOMINIO}"


def ator_da_automacao(workspace_id) -> User:
    """O robô do workspace, criado na primeira vez que uma regra executa.

    Não é criado junto com o workspace de propósito: instalação que nunca usa
    automação não ganha um usuário fantasma no banco.
    """
    email = _email_do_robo(workspace_id)
    robo = User.objects.filter(email=email).first()
    if robo is not None:
        return robo

    try:
        with transaction.atomic():
            robo = User.objects.create(
                username=f"automacao-{workspace_id}",
                email=email,
                display_name=NOME_DE_EXIBICAO,
                first_name=NOME_DE_EXIBICAO,
                is_bot=True,
                bot_type=BOT_TYPE,
                # Ativo para que os serializers o tratem como usuário normal ao
                # montar `actor_detail` — é assim que o nome chega à tela.
                is_active=True,
                is_email_verified=False,
            )
            # Sem senha utilizável: o robô é um rótulo de autoria, não uma conta.
            robo.set_unusable_password()
            robo.save(update_fields=["password"])
    except IntegrityError:
        # Dois workers pedindo o robô ao mesmo tempo na primeira execução. Quem
        # perdeu a corrida lê o que o outro gravou.
        robo = User.objects.filter(email=email).first()

    return robo
