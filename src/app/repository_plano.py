"""Repositório do Plano do aluno e da Tabela de preços da clínica (feature fluxo-caixa, F2).

Duas coisas moram aqui, as duas na **partição de nível clínica** (`PK=CLINIC#<clinicId>`,
onde já vivem `METADATA`, `APARELHO#<id>` e `ESCALA#…`):

    SK = FIN#PLANO#<pacienteId>    o plano do aluno (valor mensal + dia de vencimento)
    SK = FIN#CONFIG                a tabela de preços por frequência + avulsa/reposição

**Por que o plano NÃO fica sob a PK do paciente:** o acesso dominante é a tela de
mensalidades, que precisa de **todos os planos de uma vez** — na partição da clínica isso
é 1 Query (`begins_with "FIN#PLANO#"`); sob a PK do paciente seria um `get_item` por
aluno (30-60 por carregamento de tela). É a mesma decisão da escala (AD-013): modela-se
para o acesso dominante, e o acesso dominante aqui é a clínica inteira, não a ficha de um
aluno.

**A fonte da verdade do valor é o plano — nunca a escala.** A grade só sugere a
frequência na hora de definir o valor; uma clínica que não usa a Escala tem a tela de
mensalidades funcionando igual, com os alunos vindos do cadastro.

**Valor zero é válido e significativo:** bolsista/cortesia tem plano com
`valorCentavos=0` — diferente de "aluno sem plano", que é quem ainda não teve o valor
definido. Os dois estados aparecem diferentes na tela.

Remoção do plano é **física** (o plano é *estado atual*, como a escala — o histórico de
quem pagou o quê vive nos lançamentos, que são soft-deleted).
"""
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

_SK_PLANO_PREFIX = "FIN#PLANO#"
_SK_CONFIG = "FIN#CONFIG"
_CHAVES_INTERNAS = ("PK", "SK")
_CONDICAO_FALHOU = "ConditionalCheckFailedException"
_CAMPOS_PLANO = ("valorCentavos", "diaVencimento", "frequencia", "observacao")


def _pk(clinic_id: str) -> str:
    return f"CLINIC#{clinic_id}"


def _sk_plano(paciente_id: str) -> str:
    return f"{_SK_PLANO_PREFIX}{paciente_id}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inteiros(valor):
    """Converte `Decimal` (como o DynamoDB devolve números) em `int`, recursivamente."""
    if isinstance(valor, Decimal):
        return int(valor)
    if isinstance(valor, list):
        return [_inteiros(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _inteiros(v) for k, v in valor.items()}
    return valor


def _para_dominio(item: dict) -> dict:
    return {k: _inteiros(v) for k, v in item.items() if k not in _CHAVES_INTERNAS}


class PlanoRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    # --- Plano do aluno ---------------------------------------------------

    def upsert(self, paciente_id: str, campos: dict) -> dict:
        """Define/atualiza o plano do aluno. Idempotente — não existe "criar duas vezes".

        É `put_item` sem condição de propósito: a tela edita o valor de um aluno direto
        na linha, e exigir "existe ou não existe" ali só criaria um passo a mais.
        """
        agora = _agora_iso()
        dados = {c: campos.get(c) for c in _CAMPOS_PLANO}
        existente = self.get(paciente_id)
        item = {
            "PK": _pk(self._clinic_id),
            "SK": _sk_plano(paciente_id),
            "clinicId": self._clinic_id,
            "pacienteId": paciente_id,
            **dados,
            "criadoEm": (existente or {}).get("criadoEm", agora),
            "atualizadoEm": agora,
        }
        self._table.put_item(Item=item)
        return _para_dominio(item)

    def get(self, paciente_id: str) -> Optional[dict]:
        resp = self._table.get_item(
            Key={"PK": _pk(self._clinic_id), "SK": _sk_plano(paciente_id)}
        )
        item = resp.get("Item")
        return _para_dominio(item) if item else None

    def list_all(self) -> list[dict]:
        """Todos os planos da clínica — **1 Query**, que é o que a tela precisa.

        Pagina com `LastEvaluatedKey`: uma tela de mensalidades truncada em silêncio
        esconderia inadimplente, que é exatamente o que a feature existe para mostrar.
        """
        itens: list[dict] = []
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(_pk(self._clinic_id))
            & Key("SK").begins_with(_SK_PLANO_PREFIX),
        }
        while True:
            resp = self._table.query(**kwargs)
            itens.extend(_para_dominio(i) for i in resp.get("Items", []))
            ultima = resp.get("LastEvaluatedKey")
            if not ultima:
                break
            kwargs["ExclusiveStartKey"] = ultima
        return itens

    def delete(self, paciente_id: str) -> bool:
        """Tira o plano do aluno (remoção física). `False` se ele não tinha plano."""
        try:
            self._table.delete_item(
                Key={"PK": _pk(self._clinic_id), "SK": _sk_plano(paciente_id)},
                ConditionExpression="attribute_exists(PK)",
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == _CONDICAO_FALHOU:
                return False
            raise
        return True

    # --- Tabela de preços da clínica --------------------------------------

    def get_config(self) -> dict:
        """Tabela de preços. Clínica que nunca configurou devolve o padrão vazio.

        Nunca devolve `None`: "ainda não configurei os preços" é um estado normal, e a
        tela de mensalidades precisa funcionar antes de alguém abrir a tela de preços.
        """
        resp = self._table.get_item(Key={"PK": _pk(self._clinic_id), "SK": _SK_CONFIG})
        item = resp.get("Item")
        if not item:
            return {"tabelaPrecos": [], "aulaAvulsaCentavos": 0, "reposicaoCentavos": 0}
        cfg = _para_dominio(item)
        cfg.setdefault("tabelaPrecos", [])
        cfg.setdefault("aulaAvulsaCentavos", 0)
        cfg.setdefault("reposicaoCentavos", 0)
        return cfg

    def set_config(self, campos: dict) -> dict:
        item = {
            "PK": _pk(self._clinic_id),
            "SK": _SK_CONFIG,
            "clinicId": self._clinic_id,
            "tabelaPrecos": campos.get("tabelaPrecos") or [],
            "aulaAvulsaCentavos": campos.get("aulaAvulsaCentavos") or 0,
            "reposicaoCentavos": campos.get("reposicaoCentavos") or 0,
            "atualizadoEm": _agora_iso(),
        }
        self._table.put_item(Item=item)
        return _para_dominio(item)
