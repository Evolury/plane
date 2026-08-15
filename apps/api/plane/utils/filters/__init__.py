# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Filters module for handling complex filtering operations

# Import all utilities from base modules
from .filter_backend import ComplexFilterBackend
from .converters import LegacyToRichFiltersConverter
from .filterset import BaseFilterSet, IssueFilterSet

# Evolury: filtro por propriedade personalizada (ADR 0011)
from .propriedades import FiltroComPropriedades


# Public API exports
__all__ = [
    "ComplexFilterBackend",
    "FiltroComPropriedades",
    "LegacyToRichFiltersConverter",
    "BaseFilterSet",
    "IssueFilterSet",
]
