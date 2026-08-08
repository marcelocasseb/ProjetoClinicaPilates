"""Repositório de Imagens — metadado sob o paciente (AD-005, AD-007).

Convenção de chaves (a imagem pende do paciente, mesma PK do perfil):
    PK = CLINIC#<clinicId>#CLIENT#<pacienteId>
    SK = IMAGE#<id>

Guarda apenas o **metadado** (o binário fica no S3, ver `s3_images.py`): `key` do
objeto, `contentType` e `criadoEm`. Convive sob a mesma PK do `SK=PROFILE` → a ficha
completa do paciente (perfil + avaliações + sessões + imagens) sai em 1 Query.

O repositório é escopado por `(clinic_id, paciente_id)`, garantindo isolamento
multi-tenant. A remoção é **física** (imagem é custo de storage, não histórico clínico):
o item é apagado e, no router, o objeto correspondente é removido do S3.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

_SK_PREFIX = "IMAGE#"
_CHAVES_INTERNAS = ("PK", "SK")


def _pk(clinic_id: str, paciente_id: str) -> str:
    return f"CLINIC#{clinic_id}#CLIENT#{paciente_id}"


def _sk(imagem_id: str) -> str:
    return f"{_SK_PREFIX}{imagem_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_imagem(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}


class ImagemRepository:
    def __init__(self, clinic_id: str, paciente_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._paciente_id = paciente_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def _key(self, imagem_id: str) -> dict:
        return {"PK": _pk(self._clinic_id, self._paciente_id), "SK": _sk(imagem_id)}

    def novo_id(self) -> str:
        return str(uuid.uuid4())

    def list(self) -> list[dict]:
        """Lista as imagens confirmadas do paciente, mais antiga primeiro."""
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(_pk(self._clinic_id, self._paciente_id))
            & Key("SK").begins_with(_SK_PREFIX),
        )
        imagens = [_para_imagem(i) for i in resp.get("Items", [])]
        imagens.sort(key=lambda i: i.get("criadoEm") or "")
        return imagens

    def contar(self) -> int:
        """Quantas imagens confirmadas o paciente já tem (para o limite de 5)."""
        return len(self.list())

    def get(self, imagem_id: str) -> Optional[dict]:
        """Retorna o metadado da imagem se existir; senão `None`."""
        resp = self._table.get_item(Key=self._key(imagem_id))
        item = resp.get("Item")
        return _para_imagem(item) if item else None

    def add(self, imagem_id: str, key: str, content_type: str) -> dict:
        """Grava o metadado de uma imagem já confirmada no S3."""
        item = {
            **self._key(imagem_id),
            "id": imagem_id,
            "clinicId": self._clinic_id,
            "pacienteId": self._paciente_id,
            "key": key,
            "contentType": content_type,
            "criadoEm": _agora_iso(),
        }
        self._table.put_item(Item=item)
        return _para_imagem(item)

    def delete(self, imagem_id: str) -> None:
        """Remove fisicamente o metadado da imagem."""
        self._table.delete_item(Key=self._key(imagem_id))
