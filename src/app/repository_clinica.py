"""Repositório de metadados da clínica — nome de exibição (multi-tenant, AD-005/AD-007).

Item de metadados da clínica na tabela única:
    PK = CLINIC#<clinicId>
    SK = METADATA
    Atributos: nome (string de exibição)

Membros da equipe, na mesma partição:
    PK = CLINIC#<clinicId>
    SK = MEMBRO#<email>
    Atributos: email, nome, role, criadoEm

O login continua sendo do Cognito; este registro é o cadastro da pessoa no banco
da clínica (quem é da equipe, com nome), independente do token.

Fica numa partição própria da clínica (sem `#CLIENT#`), sem colidir com os itens de
paciente. O `clinicId` sempre vem do contexto de autenticação (token), nunca do corpo.
O nome da tabela vem de `TABLE_NAME`; o recurso boto3 é resolvido preguiçosamente
(funciona no Lambda e sob moto nos testes).
"""
import os
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

_SK_METADATA = "METADATA"
_SK_MEMBRO = "MEMBRO#"


def _pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


class ClinicaRepository:
    def __init__(self, table_name: Optional[str] = None, ddb=None):
        resource = ddb or boto3.resource("dynamodb")
        self._table = resource.Table(table_name or os.environ["TABLE_NAME"])

    def get_nome(self, clinic_id: str) -> Optional[str]:
        """Nome de exibição da clínica, ou None se não houver metadados."""
        resp = self._table.get_item(Key={"PK": _pk(clinic_id), "SK": _SK_METADATA})
        item = resp.get("Item")
        return item.get("nome") if item else None

    def set_nome(self, clinic_id: str, nome: str) -> None:
        """Grava (upsert) o nome de exibição da clínica."""
        self._table.put_item(
            Item={"PK": _pk(clinic_id), "SK": _SK_METADATA, "nome": nome}
        )

    def set_membro(self, clinic_id: str, email: str, nome: str, role: str) -> dict:
        """Grava (upsert) o registro de um membro da equipe da clínica."""
        item = {
            "PK": _pk(clinic_id),
            "SK": f"{_SK_MEMBRO}{email}",
            "email": email,
            "nome": nome,
            "role": role,
            "criadoEm": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self._table.put_item(Item=item)
        return item

    def list_membros(self, clinic_id: str) -> list[dict]:
        """Membros da equipe da clínica (só a partição dela — multi-tenant)."""
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(_pk(clinic_id))
            & Key("SK").begins_with(_SK_MEMBRO)
        )
        return resp.get("Items", [])
