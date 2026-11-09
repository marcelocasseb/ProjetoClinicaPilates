"""Aulas registradas (Pilates) de vários alunos num período, para os relatórios.

As aulas moram sob a PK de cada aluno (`PK=CLINIC#<clinicId>#CLIENT#<pacienteId>`,
`SK=SESSION#<id>`), o que deixa a ficha do aluno em 1 Query, mas não tem índice por
clínica + data. Somar a clínica inteira exige **uma Query por aluno**. Elas rodam em
paralelo: com 300 alunos e 16 linhas de execução, são ~19 rodadas de ~30 ms.

Alternativa já desenhada, se o volume crescer: indexar as sessões por mês no GSI1
(PENDENCIAS, seção 6, item 4). Nesta fase, a tabela de produção não muda.

Isolamento: a PK é montada com o `clinic_id` do token. Um `pacienteId` de outra clínica
gera uma PK que não existe nesta clínica e volta vazio.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import boto3
from boto3.dynamodb.types import TypeDeserializer

_SK_PREFIX = "SESSION#"
_CHAVES_INTERNAS = ("PK", "SK")
_MAX_WORKERS = 16

_deserializar = TypeDeserializer().deserialize


def _pk(clinic_id: str, paciente_id: str) -> str:
    return f"CLINIC#{clinic_id}#CLIENT#{paciente_id}"


def _para_sessao(item: dict) -> dict:
    return {k: _deserializar(v) for k, v in item.items() if k not in _CHAVES_INTERNAS}


def _sessoes_do_aluno(client, table: str, clinic_id: str, paciente_id: str, de: str, ate: str):
    kwargs = {
        "TableName": table,
        "KeyConditionExpression": "PK = :pk AND begins_with(SK, :sk)",
        "FilterExpression": "ativo = :sim AND #data BETWEEN :de AND :ate",
        "ExpressionAttributeNames": {"#data": "data"},
        "ExpressionAttributeValues": {
            ":pk": {"S": _pk(clinic_id, paciente_id)},
            ":sk": {"S": _SK_PREFIX},
            ":sim": {"BOOL": True},
            ":de": {"S": de},
            ":ate": {"S": ate},
        },
    }
    itens = []
    while True:
        resp = client.query(**kwargs)
        itens.extend(_para_sessao(i) for i in resp.get("Items", []))
        ultima = resp.get("LastEvaluatedKey")
        if not ultima:
            return itens
        kwargs["ExclusiveStartKey"] = ultima


def list_sessoes_periodo(
    clinic_id: str,
    paciente_ids: list[str],
    de: str,
    ate: str,
    table_name: Optional[str] = None,
) -> list[dict]:
    """Aulas **ativas** dos alunos informados com `de <= data <= ate` (`AAAA-MM-DD`).

    Cada aula volta com `pacienteId` (já gravado no item). Usa um **client** boto3 de
    baixo nível, que é thread-safe; o `resource` usado nos outros repositórios não é.
    """
    if not paciente_ids:
        return []
    table = table_name or os.environ["TABLE_NAME"]
    client = boto3.client("dynamodb")
    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(paciente_ids))) as pool:
        lotes = pool.map(
            lambda pid: _sessoes_do_aluno(client, table, clinic_id, pid, de, ate),
            paciente_ids,
        )
        return [s for lote in lotes for s in lote]
