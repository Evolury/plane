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
        # Evolury: uma entrada por offset (ADR 0006). O Brasil tem quatro
        # offsets e 16 zonas IANA, mas as zonas que compartilham offset só
        # diferem em regras de horário de verão anteriores a 2019, quando o
        # país o aboliu — para datas de hoje em diante são equivalentes.
        # Cada opção leva a cidade principal do seu offset.
        timezone_locations = [
            ("Fernando de Noronha", "America/Noronha"),  # UTC-02:00
            ("Brasília", "America/Sao_Paulo"),  # UTC-03:00
            ("Manaus", "America/Manaus"),  # UTC-04:00
            ("Rio Branco", "America/Rio_Branco"),  # UTC-05:00
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
