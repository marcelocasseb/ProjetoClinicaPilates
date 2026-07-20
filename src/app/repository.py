"""Repositório de Pacientes — acesso à tabela DynamoDB única (AD-005).

Convenção de chaves do item de perfil:
    PK = CLIENT#<id>
    SK = PROFILE

A remoção é lógica (soft delete): `ativo=False`; o item nunca é apagado
fisicamente, preservando o histórico clínico pendurado no mesmo `CLIENT#<id>`.

O nome da tabela vem de `TABLE_NAME` (injetada pelo template SAM). O recurso
boto3 é resolvido de forma preguiçosa para funcionar tanto no Lambda quanto sob
`moto` nos testes (a env var e o mock são preparados antes da primeira chamada).
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr

_SK_PROFILE = "PROFILE"
_PERFIL_CAMPOS = ("nome", "dataNascimento", "endereco", "telefone", "email")


def _pk(paciente_id: str) -> str:
    return f"CLIENT#{paciente_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_paciente(item: dict) -> dict:
    """Remove as chaves internas (PK/SK) da representação de domínio."""
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}


class PacienteRepository:
    def __init__(self, table_name: Optional[str] = None):
        self._table_name = table_name or os.environ["TABLE_NAME"]
        self._table = boto3.resource("dynamodb").Table(self._table_name)

    def create(self, data: dict) -> dict:
        """Cria o perfil do paciente e retorna o item de domínio criado."""
        paciente_id = str(uuid.uuid4())
        agora = _agora_iso()
        perfil = {campo: data.get(campo) for campo in _PERFIL_CAMPOS}
        item = {
            "PK": _pk(paciente_id),
            "SK": _SK_PROFILE,
            "id": paciente_id,
            **perfil,
            "ativo": True,
            "criadoEm": agora,
            "atualizadoEm": agora,
        }
        self._table.put_item(Item=item)
        return _para_paciente(item)

    def get(self, paciente_id: str) -> Optional[dict]:
        """Retorna o paciente se existir E estiver ativo; senão `None`."""
        resp = self._table.get_item(Key={"PK": _pk(paciente_id), "SK": _SK_PROFILE})
        item = resp.get("Item")
        if item is None or not item.get("ativo", False):
            return None
        return _para_paciente(item)

    def list_ativos(self) -> list[dict]:
        """Lista todos os perfis ativos (`SK=PROFILE`, `ativo=True`)."""
        resp = self._table.scan(
            FilterExpression=Attr("SK").eq(_SK_PROFILE) & Attr("ativo").eq(True)
        )
        return [_para_paciente(i) for i in resp.get("Items", [])]

    def update(self, paciente_id: str, data: dict) -> Optional[dict]:
        """Atualiza os campos de perfil; retorna o item ou `None` se inexistente/removido."""
        if self.get(paciente_id) is None:
            return None
        perfil = {campo: data.get(campo) for campo in _PERFIL_CAMPOS}
        agora = _agora_iso()
        nomes = {f"#{c}": c for c in _PERFIL_CAMPOS}
        valores = {f":{c}": perfil[c] for c in _PERFIL_CAMPOS}
        valores[":atualizadoEm"] = agora
        set_expr = ", ".join(f"#{c} = :{c}" for c in _PERFIL_CAMPOS)
        resp = self._table.update_item(
            Key={"PK": _pk(paciente_id), "SK": _SK_PROFILE},
            UpdateExpression=f"SET {set_expr}, atualizadoEm = :atualizadoEm",
            ExpressionAttributeNames=nomes,
            ExpressionAttributeValues=valores,
            ReturnValues="ALL_NEW",
        )
        return _para_paciente(resp["Attributes"])

    def soft_delete(self, paciente_id: str) -> bool:
        """Marca o paciente como inativo. Retorna `False` se inexistente/já removido."""
        if self.get(paciente_id) is None:
            return False
        self._table.update_item(
            Key={"PK": _pk(paciente_id), "SK": _SK_PROFILE},
            UpdateExpression="SET ativo = :falso, atualizadoEm = :agora",
            ExpressionAttributeValues={":falso": False, ":agora": _agora_iso()},
        )
        return True
