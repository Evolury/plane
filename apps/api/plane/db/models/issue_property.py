# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Propriedades personalizadas da tarefa (ADR 0011).

Três tabelas, na forma que `Estimate` + `EstimatePoint` já usa neste banco:
configuração por projeto, tabela de opções, valor por tarefa.

**Do projeto, e não do workspace.** É a lição mais cara do Jira: o que degrada
não é a quantidade de campos, é a quantidade de campos no contexto de cada
tarefa. Aqui não existe contexto global para degradar.

**O valor mora em colunas tipadas**, e não num JSON nem numa coluna de texto.
Ordenar número e data viraria cast em toda consulta, e dinheiro em texto é
defeito esperando acontecer — por isso `value_number` é `DECIMAL`.
"""

# Django imports
from django.db import models
from django.db.models import Q

# Module imports
from .project import ProjectBaseModel

# Teto por projeto. O Asana corta em 100; este é o formato simples, e o teto é
# o que protege a leitura em bloco e o layout de tabela — trinta colunas já é
# mais do que cabe numa tela.
TETO_DE_PROPRIEDADES = 30


class PropertyType(models.TextChoices):
    """Os seis tipos da v1.

    Pessoa, fórmula, rollup e checkbox ficaram de fora com motivo registrado no
    ADR 0011 — o corte é a filosofia do Linear aplicada ao pedido de um formato
    mais simples: poucos tipos que funcionam em filtro, agrupamento, ordenação
    e exportação, em vez de muitos que funcionam em alguns.
    """

    TEXT = "text", "Texto"
    NUMBER = "number", "Número"
    DATE = "date", "Data"
    SELECT = "select", "Seleção única"
    MULTI_SELECT = "multi_select", "Seleção múltipla"
    CURRENCY = "currency", "Moeda"


#: Os tipos cujo valor é uma opção da lista.
TIPOS_DE_SELECAO = {PropertyType.SELECT, PropertyType.MULTI_SELECT}


#: Os ícones que a propriedade pode vestir.
#:
#: Lista curta e fechada, como a das moedas, e pela mesma razão: ícone é
#: escolha de configuração, não catálogo. Aberta, ela vira campo livre que
#: chega à tela como nome de componente — e nome de componente vindo do banco
#: é exatamente o tipo de coisa que este projeto não deixa acontecer.
#:
#: A chave é o nome do ícone no `lucide`, que é o conjunto que o produto já
#: usa. Guardamos a chave, e não o desenho: trocar de biblioteca um dia é
#: refazer o mapa da tela, não migrar dado.
ICONES_DE_PROPRIEDADE = (
    "tag",
    "hash",
    "type",
    "calendar",
    "clock",
    "dollar-sign",
    "percent",
    "list",
    "layers",
    "circle-check",
    "flag",
    "star",
    "target",
    "triangle-alert",
    "users",
    "user",
    "building",
    "map-pin",
    "phone",
    "mail",
    "link",
    "file-text",
    "folder",
    "package",
    "truck",
    "shopping-cart",
    "credit-card",
    "briefcase",
    "wrench",
    "sparkles",
)

#: O ícone de cada tipo, quando ninguém escolheu.
#:
#: Existe para o padrão NÃO ser o mesmo desenho em tudo: um campo de dinheiro
#: com cara de etiqueta obriga a ler o nome para saber o que é, que é justamente
#: o trabalho que o ícone deveria poupar.
ICONE_PADRAO_POR_TIPO = {
    PropertyType.TEXT: "type",
    PropertyType.NUMBER: "hash",
    PropertyType.DATE: "calendar",
    PropertyType.SELECT: "list",
    PropertyType.MULTI_SELECT: "layers",
    PropertyType.CURRENCY: "dollar-sign",
}


class IssueProperty(ProjectBaseModel):
    """A definição de uma propriedade no projeto."""

    name = models.CharField(max_length=255)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    # Obrigatória barra a CRIAÇÃO, nunca a conclusão (ADR 0011): travar quem
    # terminou o trabalho por causa de metadado só ensina a preencher qualquer
    # coisa, que é pior que o campo vazio.
    is_required = models.BooleanField(default=False)
    # Desativar é o meio-termo que preserva: some dos formulários e dos
    # filtros, e os valores continuam gravados.
    is_active = models.BooleanField(default=True)
    show_on_card = models.BooleanField(default=False)
    # Se a propriedade vira eixo de "agrupar por" e "subagrupar por".
    #
    # Nasce LIGADO, ao contrário de `show_on_card`, porque os custos são
    # opostos: uma pastilha a mais disputa a largura do cartão com todas as
    # outras, enquanto um agrupamento a mais é uma linha num menu que só quem
    # abre vê. Agrupar é o uso natural de uma seleção — a caixa existe para
    # desligar ruído, não para ligar o óbvio.
    show_in_grouping = models.BooleanField(default=True)
    sort_order = models.FloatField(default=65535)
    # Só para moeda. A moeda é da PROPRIEDADE, não do valor: guardá-la por
    # tarefa deixaria somar reais com dólares na mesma coluna — conta errada
    # que ninguém percebe.
    currency = models.CharField(max_length=3, null=True, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)
    # Vazio quer dizer "o padrão do tipo", e não "sem ícone": assim mudar o
    # padrão de um tipo alcança quem nunca escolheu, sem migração de dado.
    icon = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        constraints = [
            # Dois campos com o mesmo nome no projeto seriam duas colunas
            # indistinguíveis na tabela e na exportação.
            models.UniqueConstraint(
                fields=["project", "name"],
                condition=Q(deleted_at__isnull=True),
                name="issue_property_unique_name_when_deleted_at_null",
            )
        ]
        verbose_name = "Issue Property"
        verbose_name_plural = "Issue Properties"
        db_table = "issue_properties"
        ordering = ("sort_order",)

    def __str__(self):
        return f"{self.name} <{self.project}>"

    @property
    def eh_selecao(self):
        return self.property_type in TIPOS_DE_SELECAO


class IssuePropertyOption(ProjectBaseModel):
    """Uma opção de uma propriedade de seleção."""

    issue_property = models.ForeignKey(IssueProperty, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=255, blank=True)
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["issue_property", "name"],
                condition=Q(deleted_at__isnull=True),
                name="issue_property_option_unique_name_when_deleted_at_null",
            )
        ]
        verbose_name = "Issue Property Option"
        verbose_name_plural = "Issue Property Options"
        db_table = "issue_property_options"
        ordering = ("sort_order",)

    def __str__(self):
        return f"{self.name} <{self.issue_property}>"


class IssuePropertyValue(ProjectBaseModel):
    """O valor de uma propriedade numa tarefa.

    **Uma linha por valor.** Seleção múltipla tem N linhas, uma por opção
    escolhida; todo o resto tem no máximo uma. É o que dispensa uma tabela de
    junção — e junção M2M não filtra `deleted_at`, armadilha que já mordeu esta
    base duas vezes.

    As duas restrições abaixo são o que garante isso no BANCO, e não na
    confiança do caminho de escrita.
    """

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="property_values")
    issue_property = models.ForeignKey(IssueProperty, on_delete=models.CASCADE, related_name="values")
    value_text = models.TextField(null=True, blank=True)
    value_number = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_option = models.ForeignKey(
        IssuePropertyOption, on_delete=models.CASCADE, null=True, blank=True, related_name="values"
    )

    class Meta:
        constraints = [
            # Seleção: a mesma opção não entra duas vezes na mesma tarefa.
            models.UniqueConstraint(
                fields=["issue", "issue_property", "value_option"],
                condition=Q(deleted_at__isnull=True),
                name="issue_property_value_unique_option_when_deleted_at_null",
            ),
            # Os demais tipos: uma linha só. Precisa ser uma restrição separada
            # porque o Postgres trata NULLs como distintos — sem ela, a de cima
            # deixaria passar dois textos para a mesma propriedade.
            models.UniqueConstraint(
                fields=["issue", "issue_property"],
                condition=Q(deleted_at__isnull=True, value_option__isnull=True),
                name="issue_property_value_unique_scalar_when_deleted_at_null",
            ),
        ]
        indexes = [
            # A leitura é sempre "os valores destas tarefas": os layouts
            # carregam centenas de tarefas por página, e nenhuma leitura pode
            # custar consulta por tarefa (ADR 0011).
            models.Index(fields=["issue", "issue_property"], name="issue_property_value_lookup"),
        ]
        verbose_name = "Issue Property Value"
        verbose_name_plural = "Issue Property Values"
        db_table = "issue_property_values"
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.issue_property} = {self.value_option or self.value_text or self.value_number or self.value_date}"
