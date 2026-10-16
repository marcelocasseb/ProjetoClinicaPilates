"""Repositório da Agenda — item no nível da clínica (AD-005, AD-007).

Convenção de chaves (nível clínica, ao lado da Escala e do catálogo de aparelhos):
    PK = CLINIC#<clinicId>
    SK = AGENDA#<data>#<hora>#<id>      ex.: AGENDA#2026-10-19#07:00#a3f2-…

Um agendamento é uma marcação **datada** (vale só naquele dia). O SK ordena
`data` → `hora`, então **um período inteiro = 1 Query** com `SK between`, já na ordem
de exibição. Não precisa de GSI e não colide com `ESCALA#`, `APARELHO#` nem `METADATA`.

O `id` (uuid) no fim do SK permite marcar **pessoas sem cadastro** (sem `pacienteId`) e
mais de uma pessoa no mesmo horário. A duplicata de um *paciente cadastrado* no mesmo
dia+hora é conferida no `create` (Query no prefixo do horário — barata, poucos itens).

**Remoção é FÍSICA**, como na Escala: desmarcar é desfazer a marcação, não histórico
(quem quer histórico de aula dada tem os itens `SESSION#`).

**Retenção de 4 meses**: cada item leva `expiraEm` (epoch em segundos) = data da aula
+ `MESES_RETENCAO`, e o TTL da tabela (template.yaml) apaga sozinho. Conta da data da
aula, não da criação — marcar com antecedência nunca faz a marcação sumir antes de
acontecer. O TTL apaga com atraso de até ~2 dias, então o `list_periodo` também
filtra os já vencidos.

O repositório é escopado por clínica (`clinic_id`), garantindo isolamento multi-tenant.
"""
import calendar
import os
import time
import uuid
from datetime import date, datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

_SK_PREFIX = "AGENDA#"
_CHAVES_INTERNAS = ("PK", "SK")
_CONDICAO_FALHOU = "ConditionalCheckFailedException"
MESES_RETENCAO = 4


def _pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


def _sk(data: str, hora: str, agenda_id: str) -> str:
    return f"{_SK_PREFIX}{data}#{hora}#{agenda_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def expira_em(data: str) -> int:
    """Epoch (s) de `data` + `MESES_RETENCAO` meses, à meia-noite UTC.

    Dia que não existe no mês de destino (31/10 + 4 meses) cai no último dia dele.
    """
    d = date.fromisoformat(data)
    mes = d.month - 1 + MESES_RETENCAO
    ano, mes = d.year + mes // 12, mes % 12 + 1
    dia = min(d.day, calendar.monthrange(ano, mes)[1])
    return int(datetime(ano, mes, dia, tzinfo=timezone.utc).timestamp())


def _para_agenda(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS and k != "expiraEm"}


def _vencido(item: dict, agora: int) -> bool:
    exp = item.get("expiraEm")
    return exp is not None and int(exp) <= agora


class AgendaRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def _key(self, data: str, hora: str, agenda_id: str) -> dict:
        return {"PK": _pk(self._clinic_id), "SK": _sk(data, hora, agenda_id)}

    def _query(self, condicao) -> list[dict]:
        """Query paginada (`LastEvaluatedKey`) — um período cheio não é truncado em silêncio."""
        itens: list[dict] = []
        agora = int(time.time())
        kwargs = {"KeyConditionExpression": Key("PK").eq(_pk(self._clinic_id)) & condicao}
        while True:
            resp = self._table.query(**kwargs)
            itens.extend(
                _para_agenda(i) for i in resp.get("Items", []) if not _vencido(i, agora)
            )
            ultima = resp.get("LastEvaluatedKey")
            if not ultima:
                break
            kwargs["ExclusiveStartKey"] = ultima
        return itens

    def list_periodo(self, de: str, ate: str) -> list[dict]:
        """Agendamentos de `de` a `ate` (inclusive, `YYYY-MM-DD`), por data → hora.

        O limite superior usa `~` (depois de dígitos e `#` na tabela ASCII) para pegar
        todos os horários do último dia.
        """
        return self._query(Key("SK").between(f"{_SK_PREFIX}{de}", f"{_SK_PREFIX}{ate}#~"))

    def paciente_no_horario(self, data: str, hora: str, paciente_id: str) -> bool:
        no_horario = self._query(Key("SK").begins_with(f"{_SK_PREFIX}{data}#{hora}#"))
        return any(i.get("pacienteId") == paciente_id for i in no_horario)

    def create(
        self,
        data: str,
        hora: str,
        paciente_id: Optional[str],
        nome: str,
        telefone: Optional[str],
    ) -> dict:
        """Marca alguém na data+hora. `nome` é snapshot (cadastrado) ou o nome digitado (novo)."""
        agenda_id = str(uuid.uuid4())
        item = {
            **self._key(data, hora, agenda_id),
            "clinicId": self._clinic_id,
            "id": agenda_id,
            "data": data,
            "hora": hora,
            "nome": nome,
            "criadoEm": _agora_iso(),
            "expiraEm": expira_em(data),
        }
        if paciente_id:
            item["pacienteId"] = paciente_id
        if telefone:
            item["telefone"] = telefone
        self._table.put_item(Item=item)
        return _para_agenda(item)

    def vincular(self, data: str, hora: str, agenda_id: str, paciente_id: str, nome: str) -> Optional[dict]:
        """Liga um agendamento de pessoa nova a um paciente. `None` se não existe
        ou já está vinculado (só pessoa nova pode ser vinculada)."""
        try:
            resp = self._table.update_item(
                Key=self._key(data, hora, agenda_id),
                UpdateExpression="SET pacienteId = :p, nome = :n",
                ConditionExpression="attribute_exists(PK) AND attribute_not_exists(pacienteId)",
                ExpressionAttributeValues={":p": paciente_id, ":n": nome},
                ReturnValues="ALL_NEW",
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == _CONDICAO_FALHOU:
                return None
            raise
        return _para_agenda(resp["Attributes"])

    def get(self, data: str, hora: str, agenda_id: str) -> Optional[dict]:
        """O agendamento, ou `None` se não existe (ou já venceu a retenção)."""
        item = self._table.get_item(Key=self._key(data, hora, agenda_id)).get("Item")
        if item is None or _vencido(item, int(time.time())):
            return None
        return _para_agenda(item)

    def set_pagamento(
        self, data: str, hora: str, agenda_id: str, pagamento: dict, antigo: Optional[str]
    ) -> bool:
        """Grava o pagamento (referência ao lançamento do Caixa). `False` se a marcação
        sumiu ou se outro pagamento entrou no meio do caminho.

        `antigo` é o `lancamentoId` de um pagamento cujo lançamento foi **cancelado no
        Caixa** — só ele pode ser sobrescrito; um pagamento ativo nunca é.
        """
        condicao = "attribute_exists(PK) AND (attribute_not_exists(pagamento)"
        valores = {":p": pagamento}
        if antigo:
            condicao += " OR pagamento.lancamentoId = :antigo"
            valores[":antigo"] = antigo
        condicao += ")"
        try:
            self._table.update_item(
                Key=self._key(data, hora, agenda_id),
                UpdateExpression="SET pagamento = :p",
                ConditionExpression=condicao,
                ExpressionAttributeValues=valores,
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == _CONDICAO_FALHOU:
                return False
            raise
        return True

    def remove_pagamento(self, data: str, hora: str, agenda_id: str) -> None:
        """Tira a referência ao pagamento. Sem a condição, o `update_item` num item
        inexistente criaria um item fantasma só com a chave."""
        try:
            self._table.update_item(
                Key=self._key(data, hora, agenda_id),
                UpdateExpression="REMOVE pagamento",
                ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != _CONDICAO_FALHOU:
                raise

    def delete(self, data: str, hora: str, agenda_id: str) -> bool:
        """Desmarca (remoção física). `False` se não existia."""
        try:
            self._table.delete_item(
                Key=self._key(data, hora, agenda_id),
                ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == _CONDICAO_FALHOU:
                return False
            raise
        return True
