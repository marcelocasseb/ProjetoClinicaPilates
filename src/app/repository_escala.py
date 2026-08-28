"""Repositório da Escala Semanal — item no nível da clínica (AD-005, AD-007).

Convenção de chaves (nível clínica, ao lado do catálogo de aparelhos):
    PK = CLINIC#<clinicId>
    SK = ESCALA#<dia>#<hora>#<pacienteId>      ex.: ESCALA#1#07:00#a3f2-…

Uma matrícula é o par **aluno + dia + horário** da grade fixa da semana. O SK ordena
`dia` → `hora` → `pacienteId`, então a Query devolve a grade **já na ordem de
renderização** (dia 1 = segunda … 7 = domingo; hora `HH:MM` com zero à esquerda, que é
o que faz a ordem alfabética coincidir com a cronológica).

**Grade inteira = 1 Query** por `PK=CLINIC#<clinicId>` + `SK begins_with "ESCALA#"`.
Não precisa de GSI. Não colide com `SK=METADATA` (nome da clínica) nem com
`SK=APARELHO#<id>` na mesma partição; a PK de paciente é mais longa
(`CLINIC#<clinicId>#CLIENT#<id>`).

**Duplicata é impossível por construção:** aluno+dia+hora *é* a chave. O `create` usa
`attribute_not_exists(PK)` e devolve `None` quando o aluno já está no horário (vira 409
no router) — sem read-modify-write, então duas pessoas mexendo na grade ao mesmo tempo
nunca sobrescrevem uma à outra.

**Remoção é FÍSICA** (desvio consciente do soft delete do resto do sistema): a escala é
*estado atual*, não histórico — quem quer histórico tem os itens `SESSION#` (aula
registrada). Com `ativo=False` a partição acumularia lixo para sempre e "tirar e
recolocar o aluno no mesmo horário" falharia contra a condição de duplicata.

O repositório é escopado por clínica (`clinic_id`), garantindo isolamento multi-tenant.
"""
import os
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

_SK_PREFIX = "ESCALA#"
_CHAVES_INTERNAS = ("PK", "SK")
_CONDICAO_FALHOU = "ConditionalCheckFailedException"


def _pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


def _sk(dia: int, hora: str, paciente_id: str) -> str:
    return f"{_SK_PREFIX}{dia}#{hora}#{paciente_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_escala(item: dict) -> dict:
    """Remove as chaves internas e normaliza `dia` (o DynamoDB devolve Decimal)."""
    escala = {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}
    if "dia" in escala:
        escala["dia"] = int(escala["dia"])
    return escala


class EscalaRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def _key(self, dia: int, hora: str, paciente_id: str) -> dict:
        return {"PK": _pk(self._clinic_id), "SK": _sk(dia, hora, paciente_id)}

    def create(self, dia: int, hora: str, paciente_id: str, paciente_nome: str) -> Optional[dict]:
        """Matricula o aluno no dia+horário. `None` se ele já estiver lá (→ 409).

        `paciente_nome` é um snapshot para consulta/depuração; a exibição usa o nome
        ao vivo do cadastro (ver `routers/escala.py`).
        """
        item = {
            **self._key(dia, hora, paciente_id),
            "clinicId": self._clinic_id,
            "dia": dia,
            "hora": hora,
            "pacienteId": paciente_id,
            "pacienteNome": paciente_nome,
            "criadoEm": _agora_iso(),
        }
        try:
            self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == _CONDICAO_FALHOU:
                return None
            raise
        return _para_escala(item)

    def list_all(self) -> list[dict]:
        """Grade completa da clínica, ordenada por dia → hora → nome.

        Pagina com `LastEvaluatedKey`: uma clínica cheia (7 dias × ~16 horários ×
        ~10 alunos) chega perto do corte de 1 MB da Query, e uma grade truncada em
        silêncio esconderia alunos.
        """
        itens: list[dict] = []
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(_pk(self._clinic_id))
            & Key("SK").begins_with(_SK_PREFIX),
        }
        while True:
            resp = self._table.query(**kwargs)
            itens.extend(_para_escala(i) for i in resp.get("Items", []))
            ultima = resp.get("LastEvaluatedKey")
            if not ultima:
                break
            kwargs["ExclusiveStartKey"] = ultima
        itens.sort(key=lambda m: (m.get("dia", 0), m.get("hora") or "", m.get("pacienteNome") or ""))
        return itens

    def delete(self, dia: int, hora: str, paciente_id: str) -> bool:
        """Tira o aluno do horário (remoção física). `False` se não estava lá."""
        try:
            self._table.delete_item(
                Key=self._key(dia, hora, paciente_id),
                ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == _CONDICAO_FALHOU:
                return False
            raise
        return True
