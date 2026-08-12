# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Temas reduzidos a sistema, claro e escuro (ADR 0007)."""

import importlib

import pytest
from django.apps import apps as django_apps

from plane.db.models import Profile, User

migration = importlib.import_module("plane.db.migrations.0132_evolury_basic_themes_only")


def _profile(email, theme):
    user = User.objects.create(email=email, username=email.split("@")[0])
    perfil = Profile.objects.filter(user=user).first() or Profile.objects.create(user=user)
    perfil.theme = theme
    perfil.save(update_fields=["theme"])
    return perfil


@pytest.mark.contract
class TestBasicThemes:
    @pytest.mark.django_db
    def test_high_contrast_falls_back_to_same_lightness(self):
        """Alto contraste vira o tema simples de mesma luminosidade."""
        claro = _profile("contraste-claro@evolury.com.br", {"theme": "light-contrast"})
        escuro = _profile("contraste-escuro@evolury.com.br", {"theme": "dark-contrast"})

        migration.normalize_theme(django_apps, None)

        claro.refresh_from_db()
        escuro.refresh_from_db()
        assert claro.theme["theme"] == "light"
        assert escuro.theme["theme"] == "dark"

    @pytest.mark.django_db
    def test_custom_theme_follows_its_own_palette(self):
        """O personalizado segue o darkPalette que o usuário tinha escolhido."""
        escuro = _profile(
            "custom-escuro@evolury.com.br",
            {"theme": "custom", "primary": "#ff0000", "background": "#000000", "darkPalette": True},
        )
        claro = _profile(
            "custom-claro@evolury.com.br",
            {"theme": "custom", "primary": "#00ff00", "background": "#ffffff", "darkPalette": False},
        )

        migration.normalize_theme(django_apps, None)

        escuro.refresh_from_db()
        claro.refresh_from_db()
        assert escuro.theme["theme"] == "dark"
        assert claro.theme["theme"] == "light"
        # as cores do tema personalizado não são mais lidas por nada
        for perfil in (escuro, claro):
            assert "primary" not in perfil.theme
            assert "background" not in perfil.theme
            assert "darkPalette" not in perfil.theme

    @pytest.mark.django_db
    def test_supported_themes_are_untouched(self):
        """Quem já está em claro, escuro ou sem preferência não muda."""
        claro = _profile("claro@evolury.com.br", {"theme": "light"})
        escuro = _profile("escuro@evolury.com.br", {"theme": "dark"})
        vazio = _profile("sistema@evolury.com.br", {})

        migration.normalize_theme(django_apps, None)

        claro.refresh_from_db()
        escuro.refresh_from_db()
        vazio.refresh_from_db()
        assert claro.theme["theme"] == "light"
        assert escuro.theme["theme"] == "dark"
        assert vazio.theme == {}
