# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Helpers de endpoint OTLP compartilhados por métricas e traces, para que ambos
usem o mesmo coletor: uma URL (OTLP_ENDPOINT) basta.

Não há endpoint default. Sem OTLP_ENDPOINT configurado as funções devolvem
None e quem chama simplesmente não exporta — esta instalação não envia
telemetria para terceiros. Ver docs/telemetria.md.
"""

import os
from urllib.parse import urlparse

# When no port in URL: https -> 443 (ingress), http -> 4317 (OTLP gRPC default)
OTLP_GRPC_DEFAULT_PORT = "4317"
HTTPS_DEFAULT_PORT = "443"


def get_otlp_base_endpoint() -> str | None:
    """URL do coletor OTLP configurado, ou None quando não há nenhum."""
    return (os.environ.get("OTLP_ENDPOINT") or "").strip() or None


def grpc_endpoint_from_url(url: str) -> str | None:
    """
    Derive gRPC host:port from an OTLP_ENDPOINT URL, or None when the value has
    no usable host.
    - https://otel.example.com -> otel.example.com:443 (nginx ingress)
    - otel.example.com:4317 -> otel.example.com:4317 (scheme-less with port)
    - otel.example.com -> otel.example.com:4317 (scheme-less, default gRPC port)
    - Explicit port in URL is always preserved.
    """
    # urlparse needs a scheme to correctly populate hostname/netloc.
    # Scheme-less values like "host:port" are misread as scheme="host", path="port".
    if "://" not in url:
        url = "//" + url
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return None
    if parsed.port is not None:
        port = str(parsed.port)
    elif parsed.scheme == "https":
        port = HTTPS_DEFAULT_PORT
    else:
        port = OTLP_GRPC_DEFAULT_PORT
    return f"{host}:{port}"


def get_otlp_grpc_endpoint() -> str | None:
    """
    Return the gRPC endpoint (host:port) for OTLP traces and metrics, or None
    when OTLP_ENDPOINT is not configured.
    """
    base = get_otlp_base_endpoint()
    return grpc_endpoint_from_url(base) if base else None


def get_otlp_http_metrics_url() -> str | None:
    """
    Return the HTTP URL for OTLP metrics (OTLP_ENDPOINT + /v1/metrics), or None
    when OTLP_ENDPOINT is not configured.
    """
    base = get_otlp_base_endpoint()
    return f"{base.rstrip('/')}/v1/metrics" if base else None
