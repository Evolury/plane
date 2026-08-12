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
collapse = importlib.import_module("plane.db.migrations.0131_evolury_one_timezone_per_offset")


@pytest.mark.contract
class TestBrazilTimezones:
    @pytest.mark.django_db
    def test_endpoint_lists_one_timezone_per_offset(self, client):
        """Uma entrada por offset: sem zonas repetidas e nada de fora do Brasil."""
        response = client.get(reverse("timezone-list"))

        assert response.status_code == status.HTTP_200_OK
        timezones = response.json()["timezones"]
        valores = [tz["value"] for tz in timezones]
        offsets = [tz["utc_offset"] for tz in timezones]

        assert set(valores) == set(User.BRAZIL_TIMEZONES)
        assert len(offsets) == len(set(offsets)), f"offset repetido na lista: {offsets}"
        assert sorted(offsets) == ["UTC-02:00", "UTC-03:00", "UTC-04:00", "UTC-05:00"]

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

    @pytest.mark.django_db
    def test_collapse_keeps_the_same_offset(self):
        """Zona removida vai para a que ficou no mesmo offset — ninguém muda de hora."""
        casos = [
            ("America/Cuiaba", "cuiaba", "America/Manaus"),
            ("America/Boa_Vista", "boavista", "America/Manaus"),
            ("America/Fortaleza", "fortaleza", "America/Sao_Paulo"),
            ("America/Eirunepe", "eirunepe", "America/Rio_Branco"),
        ]
        usuarios = []
        for tz, slug, _ in casos:
            user = User.objects.create(email=f"{slug}@evolury.com.br", username=f"{slug}_user")
            User.objects.filter(pk=user.pk).update(user_timezone=tz)
            usuarios.append(user)

        collapse.collapse_timezones(django_apps, None)

        for user, (_, _, esperado) in zip(usuarios, casos):
            user.refresh_from_db()
            assert user.user_timezone == esperado
