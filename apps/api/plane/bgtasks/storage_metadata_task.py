# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.conf import settings
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import FileAsset
from plane.settings.storage import S3Storage
from plane.utils.exception_logger import log_exception


def _limite_do_arquivo(asset) -> int:
    """O teto que vale para este arquivo: o menor entre o global e o declarado."""
    declarado = asset.size or settings.FILE_SIZE_LIMIT
    return min(settings.FILE_SIZE_LIMIT, declarado)


@shared_task
def get_asset_object_metadata(asset_id):
    """Lê no armazenamento o que de fato subiu — e recusa o que não devia caber.

    A recusa mora aqui porque aqui é o único ponto por onde **todos** os
    caminhos de upload passam: os dez lugares que marcam `is_uploaded` disparam
    esta tarefa. Espalhar a conferência pelos dez seria dez chances de esquecer
    um.

    Ela existe desde 22/08/2026, quando o upload trocou de POST assinado para
    PUT assinado (o R2 não implementa POST). A política do POST carregava
    `content-length-range` e era o próprio S3 que barrava arquivo grande; o PUT
    não tem equivalente, então quem confere somos nós — depois do envio, pelo
    tamanho real, não pelo declarado. Quem passou do teto tem o objeto apagado
    e o registro marcado como excluído.
    """
    try:
        asset = FileAsset.objects.get(pk=asset_id)
        storage = S3Storage()
        metadados = storage.get_object_metadata(object_name=asset.asset.name)

        tamanho_real = (metadados or {}).get("ContentLength")
        limite = _limite_do_arquivo(asset)
        if tamanho_real is not None and (tamanho_real > limite or tamanho_real < 1):
            storage.delete_files([asset.asset.name])
            asset.is_deleted = True
            asset.is_uploaded = False
            asset.deleted_at = timezone.now()
            asset.storage_metadata = metadados
            asset.save(update_fields=["is_deleted", "is_uploaded", "deleted_at", "storage_metadata"])
            log_exception(
                ValueError(
                    f"Upload recusado: o arquivo {asset_id} subiu com {tamanho_real} bytes, "
                    f"acima do limite de {limite}."
                )
            )
            return

        asset.storage_metadata = metadados
        asset.save(update_fields=["storage_metadata"])
        return
    except FileAsset.DoesNotExist:
        return
    except Exception as e:
        log_exception(e)
        return
