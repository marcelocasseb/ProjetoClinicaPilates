"""Repositório de Avaliações — item sob o paciente (AD-005, AD-007).

Convenção de chaves (a avaliação pende do paciente, mesma PK do perfil):
    PK = CLINIC#<clinicId>#CLIENT#<pacienteId>
    SK = AVALIACAO#<id>

Convive sob a mesma PK do `SK=PROFILE` → "ficha completa / evolução do paciente" = 1 Query.
Listagem: Query na tabela base por `PK` + `SK begins_with "AVALIACAO#"`, filtrando
`ativo=True`, ordenada por `data` desc na aplicação (volume por paciente é baixo).
**Não precisa de GSI.**

O repositório é escopado por `(clinic_id, paciente_id)`, garantindo isolamento multi-tenant.
Remoção é lógica (soft delete): `ativo=False`; o item nunca é apagado fisicamente.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

_SK_PREFIX = "AVALIACAO#"
_CHAVES_INTERNAS = ("PK", "SK")
_CAMPOS = (
    "data",
    "diagnosticoMedico",
    "queixaPrincipal",
    "hma",
    "pressaoArterial",
    "fc",
    "avaliacaoPostural",
    "medidas",
    "inspecaoGeral",
    "examesComplementares",
)


def _pk(clinic_id: str, paciente_id: str) -> str:
    return f"CLINIC#{clinic_id}#CLIENT#{paciente_id}"


def _sk(avaliacao_id: str) -> str:
    return f"{_SK_PREFIX}{avaliacao_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hoje_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _para_avaliacao(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}


class AvaliacaoRepository:
    def __init__(self, clinic_id: str, paciente_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._paciente_id = paciente_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def _key(self, avaliacao_id: str) -> dict:
        return {"PK": _pk(self._clinic_id, self._paciente_id), "SK": _sk(avaliacao_id)}

    def create(self, data: dict) -> dict:
        """Cria a avaliação sob o paciente e retorna o item de domínio criado."""
        avaliacao_id = str(uuid.uuid4())
        agora = _agora_iso()
        campos = {c: data.get(c) for c in _CAMPOS}
        campos["data"] = campos["data"] or _hoje_iso()
        item = {
            **self._key(avaliacao_id),
            "id": avaliacao_id,
            "clinicId": self._clinic_id,
            "pacienteId": self._paciente_id,
            **campos,
            "ativo": True,
            "criadoEm": agora,
            "atualizadoEm": agora,
        }
        self._table.put_item(Item=item)
        return _para_avaliacao(item)

    def get(self, avaliacao_id: str) -> Optional[dict]:
        """Retorna a avaliação do paciente se existir E estiver ativa; senão `None`."""
        resp = self._table.get_item(Key=self._key(avaliacao_id))
        item = resp.get("Item")
        if item is None or not item.get("ativo", False):
            return None
        return _para_avaliacao(item)

    def list_ativos(self) -> list[dict]:
        """Lista as avaliações ativas do paciente, mais recente (por `data`) primeiro."""
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(_pk(self._clinic_id, self._paciente_id))
            & Key("SK").begins_with(_SK_PREFIX),
            FilterExpression=Attr("ativo").eq(True),
        )
        avaliacoes = [_para_avaliacao(i) for i in resp.get("Items", [])]
        avaliacoes.sort(
            key=lambda a: (a.get("data") or "", a.get("criadoEm") or ""), reverse=True
        )
        return avaliacoes

    def update(self, avaliacao_id: str, data: dict) -> Optional[dict]:
        """Atualiza os campos; retorna o item ou `None` se inexistente/removido."""
        if self.get(avaliacao_id) is None:
            return None
        campos = {c: data.get(c) for c in _CAMPOS}
        campos["data"] = campos["data"] or _hoje_iso()
        nomes = {f"#{c}": c for c in _CAMPOS}
        valores = {f":{c}": campos[c] for c in _CAMPOS}
        valores[":atualizadoEm"] = _agora_iso()
        set_expr = ", ".join(f"#{c} = :{c}" for c in _CAMPOS)
        resp = self._table.update_item(
            Key=self._key(avaliacao_id),
            UpdateExpression=f"SET {set_expr}, atualizadoEm = :atualizadoEm",
            ExpressionAttributeNames=nomes,
            ExpressionAttributeValues=valores,
            ReturnValues="ALL_NEW",
        )
        return _para_avaliacao(resp["Attributes"])

    def soft_delete(self, avaliacao_id: str) -> bool:
        """Marca a avaliação como inativa. Retorna `False` se inexistente/já removida."""
        if self.get(avaliacao_id) is None:
            return False
        self._table.update_item(
            Key=self._key(avaliacao_id),
            UpdateExpression="SET ativo = :falso, atualizadoEm = :agora",
            ExpressionAttributeValues={":falso": False, ":agora": _agora_iso()},
        )
        return True
