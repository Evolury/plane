# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Fusos restritos ao Brasil (ADR 0006).

O Brasil tem quatro offsets — fixar um só deslocaria o horário de quem está
em Manaus, Cuiabá, Campo Grande, Porto Velho, Boa Vista ou Rio Branco.
"""

import importlib

import pytest
from django.apps import apps as django_apps
from django.urls import reverse
from rest_framework import status

from plane.db.models import User

migration = importlib.import_module("plane.db.migrations.0130_evolury_user_timezone_brazil")


@pytest.mark.contract
class TestBrazilTimezones:
    @pytest.mark.django_db
    def test_endpoint_lists_only_brazilian_timezones(self, client):
        """A lista oferecida na interface não traz zona de fora do Brasil."""
        response = client.get(reverse("timezone-list"))

        assert response.status_code == status.HTTP_200_OK
        valores = [tz["value"] for tz in response.json()["timezones"]]
        assert valores, "a lista não pode vir vazia"
        assert set(valores) <= set(User.BRAZIL_TIMEZONES)
        # os quatro offsets do país precisam estar representados
        assert {"America/Noronha", "America/Sao_Paulo", "America/Manaus", "America/Rio_Branco"} <= set(valores)

    @pytest.mark.django_db
    def test_endpoint_labels_carry_utc_offset(self, client):
        """Cada zona vem com o offset, que é como o seletor as diferencia."""
        response = client.get(reverse("timezone-list"))

        por_valor = {tz["value"]: tz for tz in response.json()["timezones"]}
        assert por_valor["America/Sao_Paulo"]["utc_offset"] == "UTC-03:00"
        assert por_valor["America/Manaus"]["utc_offset"] == "UTC-04:00"
        assert por_valor["America/Rio_Branco"]["utc_offset"] == "UTC-05:00"
        assert por_valor["America/Noronha"]["utc_offset"] == "UTC-02:00"

    @pytest.mark.django_db
    def test_new_user_defaults_to_sao_paulo(self):
        """Usuário novo nasce no horário de Brasília, não em UTC."""
        user = User.objects.create(email="novo@evolury.com.br", username="novo_user")

        assert user.user_timezone == "America/Sao_Paulo"

    @pytest.mark.django_db
    def test_migration_normalizes_foreign_timezone(self):
        """Fuso de fora da lista cai para São Paulo."""
        user = User.objects.create(email="utc@evolury.com.br", username="utc_user")
        User.objects.filter(pk=user.pk).update(user_timezone="UTC")

        migration.normalize_timezone(django_apps, None)

        user.refresh_from_db()
        assert user.user_timezone == "America/Sao_Paulo"

    @pytest.mark.django_db
    def test_migration_preserves_brazilian_timezone(self):
        """Quem está em Manaus continua em Manaus."""
        user = User.objects.create(
            email="manaus@evolury.com.br", username="manaus_user", user_timezone="America/Manaus"
        )

        migration.normalize_timezone(django_apps, None)

        user.refresh_from_db()
        assert user.user_timezone == "America/Manaus"
