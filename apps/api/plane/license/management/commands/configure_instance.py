# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import hashlib
import os

# Django imports
from django.core.management.base import BaseCommand, CommandError

# Module imports
from plane.license.models import InstanceConfiguration
from plane.utils.instance_config_variables import instance_config_variables


def _impressao(valor: str) -> str:
    """Um jeito de dizer "mudou" sem dizer o quê.

    Segredo em log de deploy é segredo vazado — já aconteceu nesta casa, com um
    token do Asaas impresso num aviso do Compose. O que se mostra é o resumo.
    """
    return hashlib.sha256((valor or "").encode()).hexdigest()[:12]


class Command(BaseCommand):
    help = "Configura as variáveis da instância a partir do ambiente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sincronizar",
            action="store_true",
            help=(
                "Reescreve as linhas que existem quando o ambiente diverge. "
                "Sem isto, o comando só cria o que falta e nunca atualiza."
            ),
        )
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Diz o que mudaria e não grava nada.",
        )

    def handle(self, *args, **options):
        from plane.license.utils.encryption import decrypt_data, encrypt_data

        sincronizar = options["sincronizar"]
        simular = options["simular"]

        mandatory_keys = ["SECRET_KEY"]
        for item in mandatory_keys:
            if not os.environ.get(item):
                raise CommandError(f"{item} env variable is required.")

        criadas = atualizadas = alinhadas = preservadas = 0

        for item in instance_config_variables:
            obj, created = InstanceConfiguration.objects.get_or_create(key=item.get("key"))
            cifrada = item.get("is_encrypted", False)
            do_ambiente = item.get("value")

            if created:
                obj.category = item.get("category")
                obj.is_encrypted = cifrada
                obj.value = encrypt_data(do_ambiente) if cifrada else do_ambiente
                obj.save()
                criadas += 1
                self.stdout.write(self.style.SUCCESS(f"{obj.key} loaded with value from environment variable."))
                continue

            if not sincronizar:
                self.stdout.write(self.style.WARNING(f"{obj.key} configuration already exists"))
                continue

            # Ambiente vazio não apaga configuração. A variável pode
            # simplesmente não estar definida neste deploy, e sobrescrever com
            # vazio desligaria e-mail, pagamento ou login sem ninguém pedir.
            if not do_ambiente:
                preservadas += 1
                self.stdout.write(f"{obj.key}: ausente no ambiente — preservada")
                continue

            atual = decrypt_data(obj.value) if obj.is_encrypted else (obj.value or "")
            if atual == do_ambiente:
                alinhadas += 1
                self.stdout.write(f"{obj.key}: já alinhada")
                continue

            if simular:
                atualizadas += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"{obj.key}: mudaria de {_impressao(atual)} para {_impressao(do_ambiente)}"
                    )
                )
                continue

            obj.value = encrypt_data(do_ambiente) if obj.is_encrypted else do_ambiente
            obj.save(update_fields=["value"])
            atualizadas += 1
            self.stdout.write(
                self.style.SUCCESS(f"{obj.key}: atualizada ({_impressao(atual)} → {_impressao(do_ambiente)})")
            )

        if sincronizar:
            verbo = "mudariam" if simular else "atualizadas"
            self.stdout.write(
                f"\nresumo: {criadas} criadas, {atualizadas} {verbo}, "
                f"{alinhadas} já alinhadas, {preservadas} preservadas por ambiente vazio"
            )
