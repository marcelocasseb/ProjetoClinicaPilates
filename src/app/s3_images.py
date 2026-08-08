"""Helper de S3 para as imagens dos pacientes (feature imagens-paciente / IMG-08).

O binário nunca trafega pela Lambda: o navegador sobe (PUT) e baixa (GET) direto do
S3 usando **URLs pré-assinadas** de curta duração que esta função gera. A Lambda só
tem IAM para assinar (PutObject/GetObject) e apagar (DeleteObject) objetos do bucket
`IMAGES_BUCKET` (injetado pelo template SAM).

Chave do objeto, isolada por clínica/paciente:
    <clinicId>/<pacienteId>/<imagemId>.<ext>

A extensão deriva do `contentType` — a confirmação do upload reconstrói a MESMA chave a
partir de `id` + `contentType` (nunca confia numa chave vinda do cliente).

O cliente boto3 é resolvido de forma preguiçosa (com SigV4 explícito, exigido para
URLs pré-assinadas funcionarem em qualquer região) para funcionar no Lambda e sob `moto`.
"""
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Tipos aceitos → extensão do arquivo no S3.
_TIPOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_EXPIRA_SEGUNDOS = 300  # URLs pré-assinadas de curta duração


def _client():
    return boto3.client("s3", config=Config(signature_version="s3v4"))


def _bucket() -> str:
    return os.environ["IMAGES_BUCKET"]


def content_type_valido(content_type: str) -> bool:
    return content_type in _TIPOS


def _extensao(content_type: str) -> str:
    return _TIPOS.get(content_type, "bin")


def montar_key(clinic_id: str, paciente_id: str, imagem_id: str, content_type: str) -> str:
    """Chave S3 determinística e isolada por clínica/paciente."""
    return f"{clinic_id}/{paciente_id}/{imagem_id}.{_extensao(content_type)}"


def url_upload(key: str, content_type: str) -> str:
    """URL pré-assinada de PUT — o navegador sobe o arquivo direto no S3.

    O `ContentType` entra na assinatura: o PUT do navegador precisa mandar o mesmo
    header `Content-Type`.
    """
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": _bucket(), "Key": key, "ContentType": content_type},
        ExpiresIn=_EXPIRA_SEGUNDOS,
    )


def url_download(key: str) -> str:
    """URL pré-assinada de GET — o navegador exibe a imagem direto do S3."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=_EXPIRA_SEGUNDOS,
    )


def objeto_existe(key: str) -> bool:
    """`True` se o objeto já foi enviado ao S3 (confirmação do upload)."""
    try:
        _client().head_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError:
        return False


def apagar(key: str) -> None:
    """Remove o objeto do S3 (remoção física da imagem)."""
    _client().delete_object(Bucket=_bucket(), Key=key)
