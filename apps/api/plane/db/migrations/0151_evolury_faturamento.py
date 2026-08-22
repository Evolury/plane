# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: assinatura por espaço de trabalho (ADR 0021).
#
# Cinco tabelas novas e nenhuma alteração em modelo herdado — o faturamento é
# domínio nosso do começo ao fim.
#
# A parte que exige atenção não são as tabelas: é a linha que cada espaço que
# **já existe** recebe. Espaço novo nasce `sem_assinatura`, que é o padrão do
# modelo e o certo: quem não contratou não tem plano. Aplicar isso ao que já
# está em produção congelaria cliente pagante no dia em que a trava for ligada.
#
# Por isso o que já existe entra em `em_cortesia`, com prazo: 90 dias a contar
# desta migração, **no plano maior e com preço zerado** — o que esses espaços já
# têm hoje, sem cobrar por isso. Prazo, e não cortesia aberta, pelo mesmo motivo que todo
# cupom tem fim (ADR 0021, decisão 10) — cortesia sem data é assinatura grátis
# para sempre, em silêncio. Com data, ela aparece no painel com um relógio
# correndo, e o comercial tem 90 dias para classificar espaço por espaço.
#
# Cada linha nasce com o seu registro no histórico: ato administrativo com
# consequência financeira nunca é silencioso.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from plane.utils.planos import AVANCADO, CICLO_MENSAL, copia_para_contrato
from plane.utils.regua import EM_CORTESIA, SEM_ASSINATURA, fim_da_cortesia_de_transicao


def conceder_cortesia_de_transicao(apps, schema_editor):
    """Todo espaço que já existe entra em cortesia com prazo."""
    from django.utils import timezone

    Workspace = apps.get_model("db", "Workspace")
    Assinatura = apps.get_model("db", "Assinatura")
    HistoricoDeAssinatura = apps.get_model("db", "HistoricoDeAssinatura")

    hoje = timezone.now().date()
    fim = fim_da_cortesia_de_transicao(hoje)

    # A cortesia carrega plano, e carrega o maior. Não é generosidade: é o que
    # esses espaços já têm hoje — analytics, API, webhooks, automação sem teto.
    # Cortesia sem plano seria pior que `sem_assinatura`, porque o motor de
    # direitos leria "nenhum recurso" e tiraria da mão de cliente pagante o que
    # ele usa desde ontem.
    #
    # Preço zerado porque cortesia não cobra; capacidade preservada porque
    # assento e cota de convidado precisam continuar valendo.
    cortesia = copia_para_contrato(AVANCADO, CICLO_MENSAL, gratuita=True)

    assinaturas = [
        Assinatura(workspace_id=workspace_id, status=EM_CORTESIA, pago_ate=fim, **cortesia)
        for workspace_id in Workspace.objects.values_list("id", flat=True)
    ]
    if not assinaturas:
        return

    Assinatura.objects.bulk_create(assinaturas, batch_size=500)

    HistoricoDeAssinatura.objects.bulk_create(
        [
            HistoricoDeAssinatura(
                assinatura_id=assinatura.id,
                evento="cortesia_de_transicao",
                de=SEM_ASSINATURA,
                para=EM_CORTESIA,
                motivo=f"Cortesia concedida pela migração 0151, válida até {fim.isoformat()}.",
            )
            for assinatura in assinaturas
        ],
        batch_size=500,
    )


def remover_cortesia_de_transicao(apps, schema_editor):
    """A volta não apaga linha nenhuma: as tabelas caem inteiras logo em seguida.

    A primeira versão apagava as assinaturas antes, por simetria. O Postgres
    recusou — `cannot ALTER TABLE "assinaturas" because it has pending trigger
    events` —, porque o DELETE deixa gatilhos de chave estrangeira pendentes na
    mesma transação em que o DROP TABLE acontece. Medido desfazendo a migração
    no planedev, não deduzido.

    Simetria bonita que quebra a volta é pior que nenhuma: reverter esta
    migração derruba as cinco tabelas, e não sobra o que limpar.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0150_evolury_capa_em_cor'),
    ]

    operations = [
        migrations.CreateModel(
            name='Assinatura',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('plano', models.CharField(blank=True, choices=[('essencial', 'Essencial'), ('profissional', 'Profissional'), ('avancado', 'Avancado')], default='', max_length=32)),
                ('ciclo', models.CharField(blank=True, choices=[('mensal', 'Mensal'), ('anual', 'Anual')], default='', max_length=16)),
                ('status', models.CharField(choices=[('sem_assinatura', 'Sem assinatura'), ('em_cortesia', 'Em cortesia'), ('ativa', 'Ativa'), ('atrasada', 'Atrasada'), ('restrita', 'Restrita'), ('bloqueada', 'Bloqueada'), ('cancelada', 'Cancelada'), ('encerrada', 'Encerrada'), ('removida', 'Removida')], db_index=True, default='sem_assinatura', max_length=24)),
                ('pago_ate', models.DateField(blank=True, db_index=True, null=True)),
                ('proxima_cobranca_em', models.DateField(blank=True, null=True)),
                ('assentos_incluidos', models.PositiveIntegerField(default=0)),
                ('assentos_extras', models.PositiveIntegerField(default=0)),
                ('convidados_por_assento', models.PositiveIntegerField(default=0)),
                ('valor_base', models.PositiveIntegerField(default=0)),
                ('valor_por_assento', models.PositiveIntegerField(default=0)),
                ('asaas_customer_id', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('asaas_subscription_id', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('asaas_checkout_id', models.CharField(blank=True, default='', max_length=64)),
                ('promocao_termina_em', models.DateField(blank=True, null=True)),
                ('cancelada_em', models.DateField(blank=True, null=True)),
                ('encerrada_em', models.DateField(blank=True, null=True)),
                ('remover_dados_em', models.DateField(blank=True, db_index=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='assinatura', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Assinatura',
                'verbose_name_plural': 'Assinaturas',
                'db_table': 'assinaturas',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='Cobranca',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('asaas_payment_id', models.CharField(max_length=64, unique=True)),
                ('status', models.CharField(db_index=True, max_length=32)),
                ('forma', models.CharField(blank=True, default='', max_length=32)),
                ('valor', models.PositiveIntegerField()),
                ('vencimento', models.DateField(db_index=True)),
                ('pago_em', models.DateField(blank=True, null=True)),
                ('link', models.TextField(blank=True, default='')),
                ('assinatura', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cobrancas', to='db.assinatura')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
            ],
            options={
                'verbose_name': 'Cobrança',
                'verbose_name_plural': 'Cobranças',
                'db_table': 'cobrancas',
                'ordering': ('-vencimento',),
            },
        ),
        migrations.CreateModel(
            name='Cupom',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('codigo', models.CharField(max_length=32, unique=True)),
                ('tipo', models.CharField(choices=[('percentual', 'Percentual'), ('cortesia', 'Cortesia')], max_length=16)),
                ('valor', models.PositiveIntegerField()),
                ('ciclos', models.PositiveIntegerField(blank=True, null=True)),
                ('validade', models.DateField(blank=True, null=True)),
                ('usos_max', models.PositiveIntegerField(blank=True, null=True)),
                ('usos', models.PositiveIntegerField(default=0)),
                ('descricao', models.TextField(blank=True, default='')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
            ],
            options={
                'verbose_name': 'Cupom',
                'verbose_name_plural': 'Cupons',
                'db_table': 'cupons',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddField(
            model_name='assinatura',
            name='cupom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assinaturas', to='db.cupom'),
        ),
        migrations.CreateModel(
            name='EventoAsaas',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('asaas_event_id', models.CharField(max_length=64, unique=True)),
                ('tipo', models.CharField(db_index=True, max_length=64)),
                ('payload', models.JSONField(default=dict)),
                ('processado_em', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('tentativas', models.PositiveIntegerField(default=0)),
                ('erro', models.TextField(blank=True, default='')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
            ],
            options={
                'verbose_name': 'Evento do Asaas',
                'verbose_name_plural': 'Eventos do Asaas',
                'db_table': 'eventos_asaas',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='HistoricoDeAssinatura',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('evento', models.CharField(db_index=True, max_length=48)),
                ('de', models.CharField(blank=True, default='', max_length=48)),
                ('para', models.CharField(blank=True, default='', max_length=48)),
                ('motivo', models.TextField(blank=True, default='')),
                ('assinatura', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico', to='db.assinatura')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
            ],
            options={
                'verbose_name': 'Histórico de assinatura',
                'verbose_name_plural': 'Históricos de assinatura',
                'db_table': 'historicos_de_assinatura',
                'ordering': ('-created_at',),
            },
        ),
        migrations.RunPython(
            conceder_cortesia_de_transicao,
            remover_cortesia_de_transicao,
        ),
    ]
