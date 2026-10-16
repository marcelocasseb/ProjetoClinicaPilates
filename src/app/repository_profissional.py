"""Repositório de Profissionais — item no nível da clínica (AD-005, AD-007).

Convenção de chaves (nível clínica, ao lado de aparelhos, escala e agenda):
    PK = CLINIC#<clinicId>
    SK = PROFISSIONAL#<id>

Lista inteira = 1 Query por PK + `SK begins_with "PROFISSIONAL#"`, sem GSI.

Remoção é **lógica** (soft delete, `ativo=False`): marcações antigas da Agenda apontam
para o profissional e precisam continuar mostrando o nome dele mesmo depois de ele
sair da clínica — por isso existe o `list_todos` (inclui os removidos).

O repositório é escopado por clínica (`clinic_id`), garantindo isolamento multi-tenant.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

_SK_PREFIX = "PROFISSIONAL#"
_CHAVES_INTERNAS = ("PK", "SK")
_CAMPOS = ("nome", "telefone")


def _pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


def _sk(profissional_id: str) -> str:
    return f"{_SK_PREFIX}{profissional_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_profissional(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}


class ProfissionalRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def _key(self, profissional_id: str) -> dict:
        return {"PK": _pk(self._clinic_id), "SK": _sk(profissional_id)}

    def create(self, data: dict) -> dict:
        profissional_id = str(uuid.uuid4())
        agora = _agora_iso()
        item = {
            **self._key(profissional_id),
            "id": profissional_id,
            "clinicId": self._clinic_id,
            **{c: data.get(c) for c in _CAMPOS},
            "ativo": True,
            "criadoEm": agora,
            "atualizadoEm": agora,
        }
        self._table.put_item(Item=item)
        return _para_profissional(item)

    def get(self, profissional_id: str) -> Optional[dict]:
        """O profissional se existir E estiver ativo; senão `None`."""
        item = self._table.get_item(Key=self._key(profissional_id)).get("Item")
        if item is None or not item.get("ativo", False):
            return None
        return _para_profissional(item)

    def list_todos(self) -> list[dict]:
        """Todos os profissionais, **inclusive removidos** (para resolver nomes antigos)."""
        itens: list[dict] = []
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(_pk(self._clinic_id))
            & Key("SK").begins_with(_SK_PREFIX),
        }
        while True:
            resp = self._table.query(**kwargs)
            itens.extend(_para_profissional(i) for i in resp.get("Items", []))
            ultima = resp.get("LastEvaluatedKey")
            if not ultima:
                break
            kwargs["ExclusiveStartKey"] = ultima
        return itens

    def list_ativos(self) -> list[dict]:
        ativos = [p for p in self.list_todos() if p.get("ativo")]
        ativos.sort(key=lambda p: (p.get("nome") or "").lower())
        return ativos

    def update(self, profissional_id: str, data: dict) -> Optional[dict]:
        """Atualiza os campos; `None` se inexistente/removido."""
        if self.get(profissional_id) is None:
            return None
        nomes = {f"#{c}": c for c in _CAMPOS}
        valores = {f":{c}": data.get(c) for c in _CAMPOS}
        valores[":agora"] = _agora_iso()
        set_expr = ", ".join(f"#{c} = :{c}" for c in _CAMPOS)
        resp = self._table.update_item(
            Key=self._key(profissional_id),
            UpdateExpression=f"SET {set_expr}, atualizadoEm = :agora",
            ExpressionAttributeNames=nomes,
            ExpressionAttributeValues=valores,
            ReturnValues="ALL_NEW",
        )
        return _para_profissional(resp["Attributes"])

    def soft_delete(self, profissional_id: str) -> bool:
        """Marca como inativo. `False` se inexistente/já removido."""
        if self.get(profissional_id) is None:
            return False
        self._table.update_item(
            Key=self._key(profissional_id),
            UpdateExpression="SET ativo = :falso, atualizadoEm = :agora",
            ExpressionAttributeValues={":falso": False, ":agora": _agora_iso()},
        )
        return True
