"""Repositório de Pacientes — acesso à tabela DynamoDB única, multi-tenant (AD-005, AD-007).

Convenção de chaves do item de perfil (multi-tenant, modelo pool):
    PK = CLINIC#<clinicId>#CLIENT#<clientId>
    SK = PROFILE

Todos os dados de um paciente (perfil e, no futuro, sessões/medidas) ficam sob a
mesma PK → "ficha completa do paciente" = 1 Query. O isolamento entre clínicas é
lógico: o repositório é instanciado **por clínica** (`clinic_id`) e nunca acessa
dados fora dela. O `clinic_id` vem do contexto de autenticação (token), nunca do
corpo da requisição.

Listagem de pacientes de uma clínica: via GSI `GSI1` (`GSI1PK = CLINIC#<clinicId>`),
que indexa apenas os itens de perfil (índice esparso), ordenados por nome (`GSI1SK`).

A remoção é lógica (soft delete): `ativo=False`; o item nunca é apagado fisicamente.

O nome da tabela vem de `TABLE_NAME` (injetada pelo template SAM). O recurso boto3 é
resolvido de forma preguiçosa para funcionar tanto no Lambda quanto sob `moto` nos testes.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

_SK_PROFILE = "PROFILE"
_GSI_NAME = "GSI1"
_CHAVES_INTERNAS = ("PK", "SK", "GSI1PK", "GSI1SK")
_PERFIL_CAMPOS = ("nome", "cpf", "dataNascimento", "endereco", "telefone", "email")


def _pk(clinic_id: str, paciente_id: str) -> str:
    return f"CLINIC#{clinic_id}#CLIENT#{paciente_id}"


def _gsi_pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_paciente(item: dict) -> dict:
    """Remove as chaves internas (PK/SK/GSI) da representação de domínio."""
    return {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}


class PacienteRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def create(self, data: dict) -> dict:
        """Cria o perfil do paciente na clínica e retorna o item de domínio criado."""
        paciente_id = str(uuid.uuid4())
        agora = _agora_iso()
        perfil = {campo: data.get(campo) for campo in _PERFIL_CAMPOS}
        item = {
            "PK": _pk(self._clinic_id, paciente_id),
            "SK": _SK_PROFILE,
            "GSI1PK": _gsi_pk(self._clinic_id),
            "GSI1SK": perfil["nome"] or "",
            "id": paciente_id,
            "clinicId": self._clinic_id,
            **perfil,
            "ativo": True,
            "criadoEm": agora,
            "atualizadoEm": agora,
        }
        self._table.put_item(Item=item)
        return _para_paciente(item)

    def get(self, paciente_id: str) -> Optional[dict]:
        """Retorna o paciente da clínica se existir E estiver ativo; senão `None`."""
        resp = self._table.get_item(Key={"PK": _pk(self._clinic_id, paciente_id), "SK": _SK_PROFILE})
        item = resp.get("Item")
        if item is None or not item.get("ativo", False):
            return None
        return _para_paciente(item)

    def list_ativos(self) -> list[dict]:
        """Lista os perfis ativos da clínica (Query no GSI1, filtrando `ativo=True`)."""
        resp = self._table.query(
            IndexName=_GSI_NAME,
            KeyConditionExpression=Key("GSI1PK").eq(_gsi_pk(self._clinic_id)),
            FilterExpression=Attr("ativo").eq(True),
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
        valores[":gsi1sk"] = perfil["nome"] or ""
        set_expr = ", ".join(f"#{c} = :{c}" for c in _PERFIL_CAMPOS)
        resp = self._table.update_item(
            Key={"PK": _pk(self._clinic_id, paciente_id), "SK": _SK_PROFILE},
            UpdateExpression=f"SET {set_expr}, atualizadoEm = :atualizadoEm, GSI1SK = :gsi1sk",
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
            Key={"PK": _pk(self._clinic_id, paciente_id), "SK": _SK_PROFILE},
            UpdateExpression="SET ativo = :falso, atualizadoEm = :agora",
            ExpressionAttributeValues={":falso": False, ":agora": _agora_iso()},
        )
        return True
