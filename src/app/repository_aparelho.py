"""Repositório de Aparelhos — item no nível da clínica (AD-005, AD-007).

Convenção de chaves (nível clínica, não pende do cliente):
    PK = CLINIC#<clinicId>
    SK = APARELHO#<id>

Listagem: Query na tabela base por `PK=CLINIC#<clinicId>` + `SK begins_with "APARELHO#"`,
filtrando `ativo=True`. **Não precisa de GSI** — todos os aparelhos da clínica compartilham
a PK. Não colide com pacientes, cuja PK é mais longa (`CLINIC#<clinicId>#CLIENT#<id>`).

O repositório é escopado por clínica (`clinic_id`), garantindo isolamento multi-tenant.
Remoção é lógica (soft delete): `ativo=False`; o item nunca é apagado fisicamente.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

_SK_PREFIX = "APARELHO#"
_CHAVES_INTERNAS = ("PK", "SK")
_CAMPOS = ("nome", "categoria", "descricao")


def _pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


def _sk(aparelho_id: str) -> str:
    return f"{_SK_PREFIX}{aparelho_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_aparelho(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}


class AparelhoRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def create(self, data: dict) -> dict:
        """Cria o aparelho na clínica e retorna o item de domínio criado."""
        aparelho_id = str(uuid.uuid4())
        agora = _agora_iso()
        campos = {c: data.get(c) for c in _CAMPOS}
        item = {
            "PK": _pk(self._clinic_id),
            "SK": _sk(aparelho_id),
            "id": aparelho_id,
            "clinicId": self._clinic_id,
            **campos,
            "ativo": True,
            "criadoEm": agora,
            "atualizadoEm": agora,
        }
        self._table.put_item(Item=item)
        return _para_aparelho(item)

    def get(self, aparelho_id: str) -> Optional[dict]:
        """Retorna o aparelho da clínica se existir E estiver ativo; senão `None`."""
        resp = self._table.get_item(Key={"PK": _pk(self._clinic_id), "SK": _sk(aparelho_id)})
        item = resp.get("Item")
        if item is None or not item.get("ativo", False):
            return None
        return _para_aparelho(item)

    def list_ativos(self) -> list[dict]:
        """Lista os aparelhos ativos da clínica (Query por PK + prefixo do SK)."""
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(_pk(self._clinic_id))
            & Key("SK").begins_with(_SK_PREFIX),
            FilterExpression=Attr("ativo").eq(True),
        )
        return [_para_aparelho(i) for i in resp.get("Items", [])]

    def update(self, aparelho_id: str, data: dict) -> Optional[dict]:
        """Atualiza os campos; retorna o item ou `None` se inexistente/removido."""
        if self.get(aparelho_id) is None:
            return None
        campos = {c: data.get(c) for c in _CAMPOS}
        agora = _agora_iso()
        nomes = {f"#{c}": c for c in _CAMPOS}
        valores = {f":{c}": campos[c] for c in _CAMPOS}
        valores[":atualizadoEm"] = agora
        set_expr = ", ".join(f"#{c} = :{c}" for c in _CAMPOS)
        resp = self._table.update_item(
            Key={"PK": _pk(self._clinic_id), "SK": _sk(aparelho_id)},
            UpdateExpression=f"SET {set_expr}, atualizadoEm = :atualizadoEm",
            ExpressionAttributeNames=nomes,
            ExpressionAttributeValues=valores,
            ReturnValues="ALL_NEW",
        )
        return _para_aparelho(resp["Attributes"])

    def soft_delete(self, aparelho_id: str) -> bool:
        """Marca o aparelho como inativo. Retorna `False` se inexistente/já removido."""
        if self.get(aparelho_id) is None:
            return False
        self._table.update_item(
            Key={"PK": _pk(self._clinic_id), "SK": _sk(aparelho_id)},
            UpdateExpression="SET ativo = :falso, atualizadoEm = :agora",
            ExpressionAttributeValues={":falso": False, ":agora": _agora_iso()},
        )
        return True
