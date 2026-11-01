"""Repositório de Tipos de treino — item no nível da clínica (AD-005, AD-007).

Convenção de chaves (nível clínica, ao lado de aparelhos e profissionais):
    PK = CLINIC#<clinicId>
    SK = TREINO#<id>

Lista inteira = 1 Query por PK + `SK begins_with "TREINO#"`, sem GSI.

A aula guarda o **texto** do treino (snapshot), não o id: renomear ou remover um tipo
não altera aulas já registradas. Por isso o nome não pode repetir na clínica (o front
marca o botão pelo nome) — `nome_em_uso` confere ignorando maiúsculas e acentos.

**Lista padrão:** antes deste cadastro os tipos eram fixos no front. Para nenhuma
clínica abrir a aula sem botões depois do deploy, a primeira listagem grava os tipos
padrão. O marcador `SK = TREINO_PADRAO` (fora do prefixo `TREINO#`) garante que isso
acontece uma vez só: se a clínica remover todos depois, a lista fica vazia mesmo.

Remoção é lógica (soft delete, `ativo=False`), como nos outros cadastros.
"""
import os
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

_SK_PREFIX = "TREINO#"
_SK_MARCADOR_PADRAO = "TREINO_PADRAO"
_CHAVES_INTERNAS = ("PK", "SK")

TIPOS_PADRAO = (
    "Membros superiores",
    "Membros inferiores",
    "Abdômen",
    "Força",
    "Mobilidade",
    "Postural",
    "Alongamento",
)


def _pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


def _sk(tipo_id: str) -> str:
    return f"{_SK_PREFIX}{tipo_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chave_nome(nome: str) -> str:
    """"Abdômen" e "abdomen" são o mesmo tipo (comparação e ordenação)."""
    sem_acento = unicodedata.normalize("NFD", nome or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold()


def _para_tipo(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}


class TipoTreinoRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def _key(self, tipo_id: str) -> dict:
        return {"PK": _pk(self._clinic_id), "SK": _sk(tipo_id)}

    def _novo_item(self, nome: str) -> dict:
        tipo_id = str(uuid.uuid4())
        agora = _agora_iso()
        return {
            **self._key(tipo_id),
            "id": tipo_id,
            "clinicId": self._clinic_id,
            "nome": nome,
            "ativo": True,
            "criadoEm": agora,
            "atualizadoEm": agora,
        }

    def _semear_padrao(self) -> None:
        """Grava os tipos padrão na primeira vez (o marcador condicional evita repetir)."""
        try:
            self._table.put_item(
                Item={"PK": _pk(self._clinic_id), "SK": _SK_MARCADOR_PADRAO, "criadoEm": _agora_iso()},
                ConditionExpression="attribute_not_exists(SK)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return
            raise
        with self._table.batch_writer() as batch:
            for nome in TIPOS_PADRAO:
                batch.put_item(Item=self._novo_item(nome))

    def create(self, data: dict) -> dict:
        item = self._novo_item(data["nome"])
        self._table.put_item(Item=item)
        return _para_tipo(item)

    def get(self, tipo_id: str) -> Optional[dict]:
        """O tipo se existir E estiver ativo; senão `None`."""
        item = self._table.get_item(Key=self._key(tipo_id)).get("Item")
        if item is None or not item.get("ativo", False):
            return None
        return _para_tipo(item)

    def list_ativos(self) -> list[dict]:
        """Tipos ativos da clínica em ordem alfabética (semeia a lista padrão na 1ª vez)."""
        self._semear_padrao()
        itens: list[dict] = []
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(_pk(self._clinic_id))
            & Key("SK").begins_with(_SK_PREFIX),
        }
        while True:
            resp = self._table.query(**kwargs)
            itens.extend(_para_tipo(i) for i in resp.get("Items", []) if i.get("ativo"))
            ultima = resp.get("LastEvaluatedKey")
            if not ultima:
                break
            kwargs["ExclusiveStartKey"] = ultima
        itens.sort(key=lambda t: _chave_nome(t.get("nome")))
        return itens

    def nome_em_uso(self, nome: str, exceto_id: Optional[str] = None) -> bool:
        """Já existe outro tipo ativo com esse nome (ignorando maiúsculas e acentos)?"""
        alvo = _chave_nome(nome)
        return any(
            t["id"] != exceto_id and _chave_nome(t.get("nome")) == alvo
            for t in self.list_ativos()
        )

    def update(self, tipo_id: str, data: dict) -> Optional[dict]:
        """Renomeia; `None` se inexistente/removido."""
        if self.get(tipo_id) is None:
            return None
        resp = self._table.update_item(
            Key=self._key(tipo_id),
            UpdateExpression="SET #nome = :nome, atualizadoEm = :agora",
            ExpressionAttributeNames={"#nome": "nome"},
            ExpressionAttributeValues={":nome": data["nome"], ":agora": _agora_iso()},
            ReturnValues="ALL_NEW",
        )
        return _para_tipo(resp["Attributes"])

    def soft_delete(self, tipo_id: str) -> bool:
        """Marca como inativo. `False` se inexistente/já removido."""
        if self.get(tipo_id) is None:
            return False
        self._table.update_item(
            Key=self._key(tipo_id),
            UpdateExpression="SET ativo = :falso, atualizadoEm = :agora",
            ExpressionAttributeValues={":falso": False, ":agora": _agora_iso()},
        )
        return True
