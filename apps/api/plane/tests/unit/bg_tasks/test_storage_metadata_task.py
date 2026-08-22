# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A guarda de tamanho do upload.

Ela existe desde 22/08/2026, quando o envio de arquivo trocou de POST assinado
para PUT assinado — o Cloudflare R2 não implementa POST assinado e nenhum
upload funcionava. A política do POST carregava `content-length-range`, e era o
S3 que recusava arquivo maior que o declarado; o PUT não tem equivalente.

Quem confere passou a ser esta tarefa, que já fazia `head_object` na
confirmação do upload. Os testes abaixo cobrem os dois lados da recusa e o
caso feliz — sem o caso feliz, uma tarefa que apagasse tudo passaria por
"guarda funcionando".
"""

from unittest.mock import patch

import pytest
from django.conf import settings

from plane.bgtasks.storage_metadata_task import get_asset_object_metadata
from plane.db.models import FileAsset
from plane.tests.factories import UserFactory, WorkspaceFactory


def _asset(tamanho_declarado):
    usuario = UserFactory()
    return FileAsset.objects.create(
        attributes={"name": "x.png", "type": "image/png", "size": tamanho_declarado},
        asset="chave/x.png",
        size=tamanho_declarado,
        user=usuario,
        created_by=usuario,
        workspace=WorkspaceFactory(owner=usuario),
        entity_type=FileAsset.EntityTypeContext.USER_AVATAR,
        is_uploaded=True,
    )


@pytest.mark.django_db
@patch("plane.bgtasks.storage_metadata_task.S3Storage")
def test_arquivo_dentro_do_limite_e_guardado(mock_storage):
    """O caso feliz: metadados gravados, arquivo intacto."""
    asset = _asset(1000)
    mock_storage.return_value.get_object_metadata.return_value = {"ContentLength": 900}

    get_asset_object_metadata(str(asset.id))

    asset.refresh_from_db()
    assert asset.storage_metadata == {"ContentLength": 900}
    assert asset.is_uploaded is True
    assert asset.is_deleted is False
    mock_storage.return_value.delete_files.assert_not_called()


@pytest.mark.django_db
@patch("plane.bgtasks.storage_metadata_task.S3Storage")
def test_arquivo_maior_que_o_declarado_e_recusado(mock_storage):
    """Declarou 1 KB e subiu 10 KB: o objeto é apagado e o registro, excluído."""
    asset = _asset(1000)
    mock_storage.return_value.get_object_metadata.return_value = {"ContentLength": 10_000}

    get_asset_object_metadata(str(asset.id))

    asset.refresh_from_db()
    assert asset.is_deleted is True
    assert asset.is_uploaded is False
    mock_storage.return_value.delete_files.assert_called_once_with(["chave/x.png"])


@pytest.mark.django_db
@patch("plane.bgtasks.storage_metadata_task.S3Storage")
def test_o_teto_global_vale_mesmo_com_declaracao_maior(mock_storage):
    """Declarar um valor alto não levanta o teto: o menor dos dois é que vale."""
    asset = _asset(settings.FILE_SIZE_LIMIT * 10)
    mock_storage.return_value.get_object_metadata.return_value = {
        "ContentLength": settings.FILE_SIZE_LIMIT + 1
    }

    get_asset_object_metadata(str(asset.id))

    asset.refresh_from_db()
    assert asset.is_deleted is True
    mock_storage.return_value.delete_files.assert_called_once()


@pytest.mark.django_db
@patch("plane.bgtasks.storage_metadata_task.S3Storage")
def test_arquivo_vazio_e_recusado(mock_storage):
    """Zero byte também era barrado pela política do POST (`content-length-range 1, n`)."""
    asset = _asset(1000)
    mock_storage.return_value.get_object_metadata.return_value = {"ContentLength": 0}

    get_asset_object_metadata(str(asset.id))

    asset.refresh_from_db()
    assert asset.is_deleted is True
    mock_storage.return_value.delete_files.assert_called_once()


@pytest.mark.django_db
@patch("plane.bgtasks.storage_metadata_task.S3Storage")
def test_sem_tamanho_no_metadado_nao_apaga_nada(mock_storage):
    """Metadado incompleto não é prova de abuso — na dúvida, não se apaga arquivo de cliente."""
    asset = _asset(1000)
    mock_storage.return_value.get_object_metadata.return_value = {}

    get_asset_object_metadata(str(asset.id))

    asset.refresh_from_db()
    assert asset.is_deleted is False
    mock_storage.return_value.delete_files.assert_not_called()
