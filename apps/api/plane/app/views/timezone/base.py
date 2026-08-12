# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import pytz
from datetime import datetime

# Django imports
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# Third party imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

# Module imports
from plane.authentication.rate_limit import AuthenticationThrottle


class TimezoneEndpoint(APIView):
    permission_classes = [AllowAny]

    throttle_classes = [AuthenticationThrottle]

    @method_decorator(cache_page(60 * 60 * 2))
    def get(self, request):
        # Evolury: o produto atende só o Brasil (ADR 0006). A lista do
        # upstream trazia 111 localidades do mundo e apenas duas do país.
        # Aqui ficam as 16 zonas IANA brasileiras — o Brasil tem quatro
        # offsets, não um: fixar um só deslocaria o horário de quem está em
        # Manaus, Cuiabá, Campo Grande, Porto Velho, Boa Vista ou Rio Branco.
        # Sem horário de verão desde 2019, então os offsets são estáveis.
        timezone_locations = [
            ("Fernando de Noronha", "America/Noronha"),  # UTC-02:00
            ("Brasília, São Paulo, Rio de Janeiro", "America/Sao_Paulo"),  # UTC-03:00
            ("Salvador", "America/Bahia"),  # UTC-03:00
            ("Fortaleza", "America/Fortaleza"),  # UTC-03:00
            ("Recife", "America/Recife"),  # UTC-03:00
            ("Maceió", "America/Maceio"),  # UTC-03:00
            ("Belém", "America/Belem"),  # UTC-03:00
            ("Santarém", "America/Santarem"),  # UTC-03:00
            ("Araguaína", "America/Araguaina"),  # UTC-03:00
            ("Manaus", "America/Manaus"),  # UTC-04:00
            ("Cuiabá", "America/Cuiaba"),  # UTC-04:00
            ("Campo Grande", "America/Campo_Grande"),  # UTC-04:00
            ("Porto Velho", "America/Porto_Velho"),  # UTC-04:00
            ("Boa Vista", "America/Boa_Vista"),  # UTC-04:00
            ("Rio Branco", "America/Rio_Branco"),  # UTC-05:00
            ("Eirunepé", "America/Eirunepe"),  # UTC-05:00
        ]

        timezone_list = []
        now = datetime.now()

        # Process timezone mapping
        for friendly_name, tz_identifier in timezone_locations:
            try:
                tz = pytz.timezone(tz_identifier)
                current_offset = now.astimezone(tz).strftime("%z")

                # converting and formatting UTC offset to GMT offset
                current_utc_offset = now.astimezone(tz).utcoffset()
                total_seconds = int(current_utc_offset.total_seconds())
                hours_offset = total_seconds // 3600
                minutes_offset = abs(total_seconds % 3600) // 60
                offset = f"{'+' if hours_offset >= 0 else '-'}{abs(hours_offset):02}:{minutes_offset:02}"

                timezone_value = {
                    "offset": int(current_offset),
                    "utc_offset": f"UTC{offset}",
                    "gmt_offset": f"GMT{offset}",
                    "value": tz_identifier,
                    "label": f"{friendly_name}",
                }

                timezone_list.append(timezone_value)
            except pytz.exceptions.UnknownTimeZoneError:
                continue

        # Sort by offset and then by label
        timezone_list.sort(key=lambda x: (x["offset"], x["label"]))

        # Remove offset from final output
        for tz in timezone_list:
            del tz["offset"]

        return Response({"timezones": timezone_list}, status=status.HTTP_200_OK)
