# Evolury: default de Profile.language passa de "en" para "pt-BR".
#
# Só altera o default aplicado a perfis NOVOS — perfis existentes mantêm o
# idioma que já tinham. Ao rebasear no upstream, se aparecer uma 0123_ deles,
# renumerar esta e ajustar `dependencies` para encadear depois da nova folha.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0122_alter_draftissue_assignees_alter_issue_assignees_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="language",
            field=models.CharField(default="pt-BR", max_length=255),
        ),
    ]
