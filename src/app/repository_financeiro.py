"""Repositório do Fluxo de Caixa — item em partição MENSAL da clínica (AD-005, AD-007).

Convenção de chaves:
    PK = CLINIC#<clinicId>#FIN#<AAAA-MM>       ex.: CLINIC#abc#FIN#2026-10
    SK = LANC#<id>                             ex.: LANC#a3f2-…

**Uma partição por mês** porque o mês é a unidade da tela: o extrato inteiro sai de
**1 Query** por `PK` + `SK begins_with "LANC#"`, e uma clínica com 10 anos de histórico
fica com 120 partições pequenas em vez de uma partição quente que só cresce.

**O mês da partição vem da `data` do lançamento, nunca de hoje** — lançar no dia 02/10
uma conta paga em 28/09 tem que cair em setembro, senão o fechamento do mês mente.

**Por que a `data` NÃO entra no SK:** ela entrava no desenho original (o SK sairia
pré-ordenado por data), mas isso tornaria o item não-endereçável por `id` e, pior,
transformaria "corrigir a data de 05 para 03" numa **movimentação de item** (put na chave
nova + delete na antiga) — duas escritas não-atômicas num livro-caixa, onde uma falha no
meio duplica ou some com dinheiro. Com `SK=LANC#<id>` a correção de data é um
`update_item` atômico, e a ordenação por data é feita na aplicação — barata, porque a
partição de um mês é pequena por construção.

**Dinheiro é `int` em centavos.** O DynamoDB devolve número como `Decimal`, então
`_para_lancamento` converte de volta para `int` — nada de float atravessa esta camada.

**GSI1 esparso, indexado por COMPETÊNCIA:** um pagamento de mensalidade (`pacienteId` +
`competencia`) ganha `GSI1PK=CLINIC#<clinicId>#FIN#COMP#<competencia>` e
`GSI1SK=<pacienteId>#<id>`. Assim a tela de mensalidades de um mês sai de **1 Query**,
alcançando pagamentos gravados em qualquer partição mensal — a mensalidade de setembro
paga em 3 de outubro vive no caixa de **outubro** (regime de caixa) mas pertence à
competência de **setembro**. Lançamento sem competência fica fora do índice.

Remoção é **lógica** (soft delete): o caixa é histórico, e histórico financeiro não se
apaga — cancelar marca `ativo=False` e o item permanece para auditoria.

O repositório é escopado por clínica (`clinic_id`), garantindo isolamento multi-tenant.
"""
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

_SK_PREFIX = "LANC#"
_GSI_NAME = "GSI1"
_CHAVES_INTERNAS = ("PK", "SK", "GSI1PK", "GSI1SK")
_CAMPOS = (
    "tipo",
    "data",
    "valorCentavos",
    "descricao",
    "formaPagamento",
    "pacienteId",
    "competencia",
)


def _pk(clinic_id: str, mes: str) -> str:
    return f"CLINIC#{clinic_id}#FIN#{mes}"


def _sk(lancamento_id: str) -> str:
    return f"{_SK_PREFIX}{lancamento_id}"


def _gsi_pk(clinic_id: str, competencia: str) -> str:
    return f"CLINIC#{clinic_id}#FIN#COMP#{competencia}"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mes_da_data(data: str) -> str:
    """`2026-09-28` → `2026-09`. A partição sai daqui (a data do fato, não de hoje)."""
    return data[:7]


def _para_lancamento(item: dict) -> dict:
    """Remove chaves internas e devolve `valorCentavos` como `int` (vem `Decimal`)."""
    lanc = {k: v for k, v in item.items() if k not in _CHAVES_INTERNAS}
    valor = lanc.get("valorCentavos")
    if isinstance(valor, Decimal):
        lanc["valorCentavos"] = int(valor)
    return lanc


class FinanceiroRepository:
    def __init__(self, clinic_id: str, table_name: Optional[str] = None):
        self._clinic_id = clinic_id
        self._table = boto3.resource("dynamodb").Table(table_name or os.environ["TABLE_NAME"])

    def _key(self, mes: str, lancamento_id: str) -> dict:
        return {"PK": _pk(self._clinic_id, mes), "SK": _sk(lancamento_id)}

    def _chaves_gsi(self, campos: dict, lancamento_id: str) -> dict:
        """Chaves do GSI1 — só para **pagamento de mensalidade** (índice esparso).

        Indexa por **competência**, não por aluno, porque a pergunta que a tela de
        mensalidades faz é "quem pagou a competência de setembro?" — e o pagamento da
        competência de setembro pode ter sido feito em 3 de outubro, ou seja, mora na
        partição de **outubro**. Indexado por competência, a tela inteira sai de 1 Query;
        indexado por aluno, seria uma Query por aluno (30-60 por carregamento de tela).

        Exige `pacienteId` **e** `competencia`: uma aula avulsa de um aluno tem paciente
        mas não tem competência, e não é mensalidade — fica fora do índice, de propósito.
        """
        paciente_id = campos.get("pacienteId")
        competencia = campos.get("competencia")
        if not paciente_id or not competencia:
            return {}
        return {
            "GSI1PK": _gsi_pk(self._clinic_id, competencia),
            # O id no fim garante unicidade: o mesmo aluno pode pagar a competência em
            # duas parcelas, e as duas precisam caber no índice.
            "GSI1SK": f"{paciente_id}#{lancamento_id}",
        }

    def create(self, data: dict) -> dict:
        """Cria o lançamento na partição do mês da sua própria `data`."""
        lancamento_id = str(uuid.uuid4())
        agora = _agora_iso()
        campos = {c: data.get(c) for c in _CAMPOS}
        mes = mes_da_data(campos["data"])
        item = {
            **self._key(mes, lancamento_id),
            **self._chaves_gsi(campos, lancamento_id),
            "id": lancamento_id,
            "clinicId": self._clinic_id,
            **campos,
            "ativo": True,
            "criadoEm": agora,
            "atualizadoEm": agora,
        }
        self._table.put_item(Item=item)
        return _para_lancamento(item)

    def get(self, mes: str, lancamento_id: str) -> Optional[dict]:
        """Retorna o lançamento se existir E estiver ativo; senão `None`."""
        resp = self._table.get_item(Key=self._key(mes, lancamento_id))
        item = resp.get("Item")
        if item is None or not item.get("ativo", False):
            return None
        return _para_lancamento(item)

    def list_mes(self, mes: str) -> list[dict]:
        """Lançamentos ativos do mês, ordenados por `data` crescente (ordem de extrato).

        Pagina com `LastEvaluatedKey`: um mês movimentado de uma clínica grande pode
        passar do corte de 1 MB da Query, e um extrato truncado em silêncio faria o
        saldo da tela mentir — o pior defeito possível nesta feature.
        """
        itens: list[dict] = []
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(_pk(self._clinic_id, mes))
            & Key("SK").begins_with(_SK_PREFIX),
            "FilterExpression": Attr("ativo").eq(True),
        }
        while True:
            resp = self._table.query(**kwargs)
            itens.extend(_para_lancamento(i) for i in resp.get("Items", []))
            ultima = resp.get("LastEvaluatedKey")
            if not ultima:
                break
            kwargs["ExclusiveStartKey"] = ultima
        itens.sort(key=lambda l: (l.get("data") or "", l.get("criadoEm") or ""))
        return itens

    def update(self, mes: str, lancamento_id: str, data: dict) -> Optional[dict]:
        """Atualiza os campos; `None` se inexistente/cancelado.

        A troca de mês é barrada no router (`400`) — aqui a `data` nova é gravada como
        atributo comum, o que mantém a correção de data dentro do mês **atômica**.
        """
        if self.get(mes, lancamento_id) is None:
            return None
        campos = {c: data.get(c) for c in _CAMPOS}
        nomes = {f"#{c}": c for c in _CAMPOS}
        valores = {f":{c}": campos[c] for c in _CAMPOS}
        valores[":atualizadoEm"] = _agora_iso()
        set_expr = ", ".join(f"#{c} = :{c}" for c in _CAMPOS)
        expressao = f"SET {set_expr}, atualizadoEm = :atualizadoEm"

        # O vínculo com o aluno pode ser posto ou tirado na edição: as chaves do GSI1
        # acompanham, senão o item ficaria indexado para um paciente que não é mais o dele.
        gsi = self._chaves_gsi(campos, lancamento_id)
        if gsi:
            nomes.update({"#GSI1PK": "GSI1PK", "#GSI1SK": "GSI1SK"})
            valores.update({":GSI1PK": gsi["GSI1PK"], ":GSI1SK": gsi["GSI1SK"]})
            expressao += ", #GSI1PK = :GSI1PK, #GSI1SK = :GSI1SK"
        else:
            expressao += " REMOVE GSI1PK, GSI1SK"

        resp = self._table.update_item(
            Key=self._key(mes, lancamento_id),
            UpdateExpression=expressao,
            ExpressionAttributeNames=nomes,
            ExpressionAttributeValues=valores,
            ReturnValues="ALL_NEW",
        )
        return _para_lancamento(resp["Attributes"])

    def soft_delete(self, mes: str, lancamento_id: str) -> bool:
        """Cancela o lançamento (`ativo=False`). `False` se inexistente/já cancelado.

        O item **permanece** na tabela: "essa despesa foi lançada e cancelada por engano"
        é informação de auditoria que um delete físico apagaria para sempre.
        """
        if self.get(mes, lancamento_id) is None:
            return False
        self._table.update_item(
            Key=self._key(mes, lancamento_id),
            UpdateExpression="SET ativo = :falso, atualizadoEm = :agora",
            ExpressionAttributeValues={":falso": False, ":agora": _agora_iso()},
        )
        return True

    def list_por_competencia(self, competencia: str) -> list[dict]:
        """Pagamentos de mensalidade de uma competência, via GSI1 — **1 Query**.

        Alcança pagamentos gravados em QUALQUER partição mensal: a mensalidade de
        setembro paga em 3 de outubro vive no caixa de outubro (regime de caixa) mas
        pertence à competência de setembro, e é assim que ela é cobrada.
        """
        itens: list[dict] = []
        kwargs = {
            "IndexName": _GSI_NAME,
            "KeyConditionExpression": Key("GSI1PK").eq(_gsi_pk(self._clinic_id, competencia)),
            "FilterExpression": Attr("ativo").eq(True),
        }
        while True:
            resp = self._table.query(**kwargs)
            itens.extend(_para_lancamento(i) for i in resp.get("Items", []))
            ultima = resp.get("LastEvaluatedKey")
            if not ultima:
                break
            kwargs["ExclusiveStartKey"] = ultima
        return itens
