from django.db import migrations, models


def disable_telemetry(apps, schema_editor):
    """Desliga a telemetria nas instâncias já registradas.

    O default anterior era `True`, então toda instalação existente foi criada
    enviando métricas. A troca do default só vale para linhas novas — esta
    migração faz valer para as que já existem.
    """
    Instance = apps.get_model("license", "Instance")
    Instance.objects.filter(is_telemetry_enabled=True).update(is_telemetry_enabled=False)


class Migration(migrations.Migration):

    dependencies = [
        ("license", "0006_instance_is_current_version_deprecated"),
    ]

    operations = [
        migrations.AlterField(
            model_name="instance",
            name="is_telemetry_enabled",
            field=models.BooleanField(default=False),
        ),
        # Sem reversa: não há como saber quais instâncias tinham a telemetria
        # ligada por escolha e quais apenas herdaram o default antigo.
        migrations.RunPython(disable_telemetry, migrations.RunPython.noop),
    ]
