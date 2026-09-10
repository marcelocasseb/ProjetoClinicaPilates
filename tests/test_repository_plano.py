"""Testes do repositório de Planos e Tabela de preços (feature fluxo-caixa, F2)."""
import boto3
import pytest

from app.repository_plano import PlanoRepository

CLINICA = "clinica-a"
OUTRA = "clinica-b"

PLANO = {"valorCentavos": 26000, "diaVencimento": 5, "frequencia": 2, "observacao": None}


@pytest.fixture
def repo(dynamo_table):
    return PlanoRepository(clinic_id=CLINICA, table_name=dynamo_table)


@pytest.fixture
def repo_outra(dynamo_table):
    return PlanoRepository(clinic_id=OUTRA, table_name=dynamo_table)


def _item_bruto(nome, clinic_id, sk):
    tabela = boto3.resource("dynamodb", region_name="us-east-1").Table(nome)
    return tabela.get_item(Key={"PK": f"CLINIC#{clinic_id}", "SK": sk}).get("Item")


# --- plano do aluno -------------------------------------------------------


def test_upsert_cria_e_devolve(repo):
    plano = repo.upsert("p1", PLANO)
    assert plano["pacienteId"] == "p1"
    assert plano["valorCentavos"] == 26000
    assert plano["diaVencimento"] == 5
    assert plano["criadoEm"] and plano["atualizadoEm"]


def test_upsert_grava_na_particao_da_clinica(repo, dynamo_table):
    """O plano mora na partição da clínica, não sob a PK do paciente (1 Query na tela)."""
    repo.upsert("p1", PLANO)
    item = _item_bruto(dynamo_table, CLINICA, "FIN#PLANO#p1")
    assert item is not None
    assert item["PK"] == f"CLINIC#{CLINICA}"


def test_upsert_e_idempotente_e_preserva_criado_em(repo):
    primeiro = repo.upsert("p1", PLANO)
    segundo = repo.upsert("p1", {**PLANO, "valorCentavos": 30000})

    assert segundo["valorCentavos"] == 30000
    assert segundo["criadoEm"] == primeiro["criadoEm"]
    assert len(repo.list_all()) == 1, "upsert não pode duplicar"


def test_valor_zero_e_valido(repo):
    """Bolsista/cortesia: plano com valor 0 — diferente de 'aluno sem plano'."""
    plano = repo.upsert("p1", {**PLANO, "valorCentavos": 0})
    assert plano["valorCentavos"] == 0
    assert repo.get("p1") is not None


def test_valor_volta_como_int_nao_decimal(repo):
    repo.upsert("p1", PLANO)
    lido = repo.get("p1")
    assert isinstance(lido["valorCentavos"], int)
    assert isinstance(lido["diaVencimento"], int)


def test_get_inexistente(repo):
    assert repo.get("nao-existe") is None


def test_list_all_vazio(repo):
    assert repo.list_all() == []


def test_list_all_traz_todos(repo):
    repo.upsert("p1", PLANO)
    repo.upsert("p2", {**PLANO, "valorCentavos": 34000})
    assert sorted(p["pacienteId"] for p in repo.list_all()) == ["p1", "p2"]


def test_list_all_nao_traz_config_nem_outros_itens(repo, dynamo_table):
    """`FIN#CONFIG`, `METADATA`, `APARELHO#` e `ESCALA#` dividem a mesma partição."""
    repo.upsert("p1", PLANO)
    repo.set_config({"tabelaPrecos": [], "aulaAvulsaCentavos": 5000})
    tabela = boto3.resource("dynamodb", region_name="us-east-1").Table(dynamo_table)
    tabela.put_item(Item={"PK": f"CLINIC#{CLINICA}", "SK": "METADATA", "nome": "Zen"})
    tabela.put_item(Item={"PK": f"CLINIC#{CLINICA}", "SK": "ESCALA#1#07:00#p1"})

    todos = repo.list_all()
    assert len(todos) == 1
    assert todos[0]["pacienteId"] == "p1"


def test_list_all_pagina_ate_o_fim(repo, monkeypatch):
    """Tela truncada em silêncio esconderia inadimplente — o motivo da feature existir."""
    for i in range(5):
        repo.upsert(f"p{i}", PLANO)

    original = repo._table.query
    chamadas = {"n": 0}

    def query_paginada(**kwargs):
        resp = original(**kwargs)
        itens = resp.get("Items", [])
        if chamadas["n"] < 4 and len(itens) > 1:
            chamadas["n"] += 1
            corte = itens[0]
            return {"Items": [corte], "LastEvaluatedKey": {"PK": corte["PK"], "SK": corte["SK"]}}
        return resp

    monkeypatch.setattr(repo._table, "query", query_paginada)
    assert len(repo.list_all()) >= 5


def test_delete_remove_de_verdade(repo, dynamo_table):
    repo.upsert("p1", PLANO)
    assert repo.delete("p1") is True
    assert _item_bruto(dynamo_table, CLINICA, "FIN#PLANO#p1") is None
    assert repo.get("p1") is None


def test_delete_repetido_e_inexistente(repo):
    repo.upsert("p1", PLANO)
    assert repo.delete("p1") is True
    assert repo.delete("p1") is False
    assert repo.delete("nunca-existiu") is False


# --- tabela de preços -----------------------------------------------------


def test_config_padrao_quando_nunca_configurada(repo):
    """Nunca 404/None: 'não configurei os preços' é estado normal."""
    cfg = repo.get_config()
    assert cfg == {"tabelaPrecos": [], "aulaAvulsaCentavos": 0, "reposicaoCentavos": 0}


def test_set_e_get_config(repo):
    repo.set_config(
        {
            "tabelaPrecos": [
                {"frequencia": 1, "valorCentavos": 16000},
                {"frequencia": 2, "valorCentavos": 26000},
            ],
            "aulaAvulsaCentavos": 5000,
            "reposicaoCentavos": 0,
        }
    )
    cfg = repo.get_config()
    assert cfg["aulaAvulsaCentavos"] == 5000
    assert len(cfg["tabelaPrecos"]) == 2
    assert cfg["tabelaPrecos"][1]["valorCentavos"] == 26000
    assert isinstance(cfg["tabelaPrecos"][1]["valorCentavos"], int), "Decimal não pode vazar"


# --- isolamento multi-tenant ---------------------------------------------


def test_outra_clinica_nao_ve_planos(repo, repo_outra):
    repo.upsert("p1", PLANO)
    assert repo_outra.list_all() == []
    assert repo_outra.get("p1") is None


def test_outra_clinica_nao_apaga_plano(repo, repo_outra):
    repo.upsert("p1", PLANO)
    assert repo_outra.delete("p1") is False
    assert repo.get("p1") is not None


def test_outra_clinica_tem_config_propria(repo, repo_outra):
    repo.set_config({"aulaAvulsaCentavos": 5000})
    assert repo_outra.get_config()["aulaAvulsaCentavos"] == 0
