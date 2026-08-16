# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: automações personalizadas — quando / se / então (ADR 0012).
#
# O modelo é o ECA clássico (evento, condição, ação): o GATILHO diz quando
# perguntar, a CONDIÇÃO diz se vale, as AÇÕES dizem o que fazer. A divisão não
# é enfeite — é ela que permite reaproveitar o filtro rico inteiro como
# condição, sem inventar um segundo vocabulário de campos.
#
# Especificação e decisões em docs/evolury/funcionalidades/automacao/.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel
from .project import ProjectBaseModel


class AutomationTrigger(models.TextChoices):
    """Os quatro gatilhos. Quatro, e não quinze, por decisão do ADR 0012."""

    WORK_ITEM_CREATED = "work_item_created", "Tarefa criada"
    # Um gatilho parametrizado cobre estado, prioridade, responsável, etiqueta,
    # datas e propriedade personalizada. Cinco gatilhos nomeados viram um, e o
    # seletor de campo é a MESMA lista do filtro — propriedade nova entra sem
    # código novo.
    FIELD_CHANGED = "field_changed", "Campo alterado"
    COMMENT_ADDED = "comment_added", "Comentário adicionado"
    # Resolve a classe "vence amanhã" / "parada há N dias": ninguém automatiza
    # o esquecimento reagindo a quem mexeu, porque o ponto é que ninguém mexeu.
    SCHEDULED = "scheduled", "Em um horário"


class AutomationRunStatus(models.TextChoices):
    MATCHED = "matched", "Executada"
    # Condição que não casa é o caminho NORMAL de uma regra, não um erro. Ela
    # para em silêncio de propósito — e é justamente por isso que precisa ficar
    # registrada: "por que não rodou?" é a pergunta número um de suporte em
    # todos os produtos que têm esse recurso.
    SKIPPED = "skipped", "Condição não casou"
    FAILED = "failed", "Falhou"


class Automation(ProjectBaseModel):
    """Uma regra do projeto."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    # --- quando ---
    trigger_type = models.CharField(max_length=32, choices=AutomationTrigger.choices)
    # A forma depende do gatilho, e quem valida é o serializer:
    #   field_changed → {"field": "state_id", "to": [...], "from": [...]}
    #   scheduled     → {"frequency": "daily"|"weekly", "weekdays": [...], "time": "08:00"}
    # Os outros dois não têm o que configurar.
    trigger_config = models.JSONField(default=dict, blank=True)

    # --- se ---
    # A MESMA árvore JSON que o quadro manda no parâmetro `filters`. No quadro
    # ela pergunta "quais tarefas mostrar?"; aqui, "esta tarefa se encaixa?" —
    # o mesmo predicado com aridade diferente. Nulo quer dizer "todas".
    condition = models.JSONField(null=True, blank=True)

    # --- então ---
    # Lista ORDENADA de ações. Ordem importa (mudar estado antes de comentar
    # muda o que o comentário diz), são poucas, e são editadas como um bloco só.
    # Quem define o que é válido é o registro de ações, não uma tabela de tipos:
    # ação que ainda não foi implementada simplesmente não está lá.
    actions = models.JSONField(default=list, blank=True)

    # --- operação ---
    # Só as agendadas usam. Indexado porque o job de 15 em 15 minutos varre por
    # ele — sem isso a varredura leria todas as regras do banco a cada rodada.
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    # Preenchido quando o motor desliga a regra sozinho (estouro de teto). Fica
    # gravado porque "minha regra parou e ninguém me disse" é pior do que a
    # regra ter parado.
    disabled_reason = models.TextField(blank=True, default="")

    class Meta:
        # Sem unicidade de nome de propósito: duas regras com o mesmo nome são
        # confusas, mas nada a jusante fica ambíguo (o log é por id, e a lista
        # mostra a frase inteira). Obrigar a renomear seria atrito sem ganho.
        verbose_name = "Automation"
        verbose_name_plural = "Automations"
        db_table = "automations"
        ordering = ("-created_at",)
        indexes = [
            # A busca do despacho: "as regras ativas deste projeto para este
            # gatilho". É feita a cada evento, então paga índice.
            models.Index(fields=["project", "trigger_type", "is_active"], name="automation_despacho_idx")
        ]

    def __str__(self):
        return f"{self.name} <{self.project.name}>"


class AutomationRun(BaseModel):
    """Uma execução — o registro que responde "por que não rodou?".

    Grava tanto o que executou quanto o que parou na condição. Sem as duas
    metades o log responde só metade da pergunta.
    """

    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name="runs")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="automation_runs")
    # Nulo na execução agendada, que é sobre um CONJUNTO de tarefas: a linha
    # resume o lote, e as tarefas alcançadas aparecem em `actions_result`.
    issue = models.ForeignKey(
        "db.Issue", on_delete=models.SET_NULL, null=True, blank=True, related_name="automation_runs"
    )
    status = models.CharField(max_length=16, choices=AutomationRunStatus.choices)
    # O que disparou, em linguagem de máquina: campo, de, para, quem.
    trigger_summary = models.JSONField(default=dict, blank=True)
    # Uma entrada por ação: o que era, o que virou, ou por que não fez nada.
    # "Já estava assim" é resultado legítimo e precisa aparecer — é o que
    # explica a regra que roda todo dia e não muda nada.
    actions_result = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True, default="")
    duration_ms = models.PositiveIntegerField(default=0)
    # Profundidade do encadeamento: 0 é ação humana, 1 é regra que respondeu a
    # outra regra. O teto vive no motor; aqui fica o rastro de quem chegou perto.
    depth = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Automation Run"
        verbose_name_plural = "Automation Runs"
        db_table = "automation_runs"
        ordering = ("-created_at",)
        indexes = [
            # Serve às duas leituras: a tela do log de uma regra, e a contagem
            # da última hora que segura o teto por regra.
            models.Index(fields=["automation", "-created_at"], name="automation_run_historico_idx")
        ]

    def __str__(self):
        return f"{self.automation_id} {self.status} @ {self.created_at}"
