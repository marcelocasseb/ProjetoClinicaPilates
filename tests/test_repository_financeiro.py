"""Testes do repositório do Fluxo de Caixa (FIN-01/02/03/07/08/10/11/12)."""
import boto3
import pytest

from app.repository_financeiro import FinanceiroRepository, mes_da_data

CLINICA = "clinica-a"
OUTRA = "clinica-b"

BASE = {
    "tipo": "saida",
    "data": "2026-10-05",
    "valorCentavos": 15000,
    "descricao": "Conta de luz",
    "formaPagamento": "pix",
    "pacienteId": None,
    "competencia": None,
}


@pytest.fixture
def repo(dynamo_table):
    return FinanceiroRepository(clinic_id=CLINICA, table_name=dynamo_table)


@pytest.fixture
def repo_outra(dynamo_table):
    return FinanceiroRepository(clinic_id=OUTRA, table_name=dynamo_table)


def _tabela(nome):
    return boto3.resource("dynamodb", region_name="us-east-1").Table(nome)


def _item_bruto(nome, clinic_id, mes, lancamento_id):
    resp = _tabela(nome).get_item(
        Key={"PK": f"CLINIC#{clinic_id}#FIN#{mes}", "SK": f"LANC#{lancamento_id}"}
    )
    return resp.get("Item")


def _cria(repo, **over):
    return repo.create({**BASE, **over})


# --- criação e chaves -----------------------------------------------------


def test_create_devolve_id_e_campos(repo):
    lanc = _cria(repo)
    assert lanc["id"]
    assert lanc["tipo"] == "saida"
    assert lanc["valorCentavos"] == 15000
    assert lanc["ativo"] is True
    assert lanc["criadoEm"] and lanc["atualizadoEm"]


def test_create_grava_pk_sk_exatos(repo, dynamo_table):
    lanc = _cria(repo)
    item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
    assert item is not None
    assert item["PK"] == f"CLINIC#{CLINICA}#FIN#2026-10"
    assert item["SK"] == f"LANC#{lanc['id']}"


def test_particao_vem_da_data_do_lancamento_nao_de_hoje(repo, dynamo_table):
    """Lançar em outubro uma conta paga em 28/09 tem que cair em setembro."""
    lanc = _cria(repo, data="2026-09-28")
    assert _item_bruto(dynamo_table, CLINICA, "2026-09", lanc["id"]) is not None
    assert _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"]) is None


def test_mes_da_data():
    assert mes_da_data("2026-09-28") == "2026-09"


def test_chaves_internas_nao_vazam_no_dominio(repo):
    lanc = _cria(repo, pacienteId="p1")
    for chave in ("PK", "SK", "GSI1PK", "GSI1SK"):
        assert chave not in lanc


def test_valor_volta_como_int_nao_decimal(repo):
    """O DynamoDB devolve `Decimal`; nada de float/Decimal atravessa o repositório."""
    lanc = _cria(repo)
    lido = repo.get("2026-10", lanc["id"])
    assert isinstance(lido["valorCentavos"], int)
    assert lido["valorCentavos"] == 15000


# --- leitura do mês -------------------------------------------------------


def test_list_mes_vazio(repo):
    assert repo.list_mes("2026-10") == []


def test_list_mes_ordena_por_data_crescente(repo):
    _cria(repo, data="2026-10-20", descricao="c")
    _cria(repo, data="2026-10-01", descricao="a")
    _cria(repo, data="2026-10-10", descricao="b")

    datas = [l["data"] for l in repo.list_mes("2026-10")]
    assert datas == ["2026-10-01", "2026-10-10", "2026-10-20"]


def test_list_mes_ignora_outro_mes(repo):
    _cria(repo, data="2026-10-05")
    _cria(repo, data="2026-09-28")
    assert len(repo.list_mes("2026-10")) == 1
    assert len(repo.list_mes("2026-09")) == 1


def test_list_mes_ignora_cancelados(repo):
    lanc = _cria(repo)
    _cria(repo, descricao="fica")
    repo.soft_delete("2026-10", lanc["id"])

    restantes = repo.list_mes("2026-10")
    assert [l["descricao"] for l in restantes] == ["fica"]


def test_list_mes_pagina_ate_o_fim(repo, monkeypatch):
    """Extrato truncado em silêncio faria o saldo mentir — o pior defeito da feature."""
    for i in range(1, 6):
        _cria(repo, data=f"2026-10-{i:02d}")

    original = repo._table.query
    chamadas = {"n": 0}

    def query_paginada(**kwargs):
        """Devolve 1 item por página nas 4 primeiras chamadas (simula LastEvaluatedKey)."""
        resp = original(**kwargs)
        itens = resp.get("Items", [])
        if chamadas["n"] < 4 and len(itens) > 1:
            chamadas["n"] += 1
            corte = itens[0]
            return {
                "Items": [corte],
                "LastEvaluatedKey": {"PK": corte["PK"], "SK": corte["SK"]},
            }
        return resp

    monkeypatch.setattr(repo._table, "query", query_paginada)
    assert len(repo.list_mes("2026-10")) >= 5


# --- get ------------------------------------------------------------------


def test_get_inexistente(repo):
    assert repo.get("2026-10", "nao-existe") is None


def test_get_mes_errado(repo):
    lanc = _cria(repo)
    assert repo.get("2026-09", lanc["id"]) is None


def test_get_cancelado(repo):
    lanc = _cria(repo)
    repo.soft_delete("2026-10", lanc["id"])
    assert repo.get("2026-10", lanc["id"]) is None


# --- update ---------------------------------------------------------------


def test_update_altera_campos(repo):
    lanc = _cria(repo)
    alterado = repo.update("2026-10", lanc["id"], {**BASE, "valorCentavos": 18000})
    assert alterado["valorCentavos"] == 18000
    assert repo.get("2026-10", lanc["id"])["valorCentavos"] == 18000


def test_update_altera_data_dentro_do_mes_em_uma_escrita(repo, dynamo_table):
    """Corrigir a data dentro do mês é `update_item` atômico — o item não se move."""
    lanc = _cria(repo, data="2026-10-05")
    repo.update("2026-10", lanc["id"], {**BASE, "data": "2026-10-03"})

    item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
    assert item["data"] == "2026-10-03"
    assert item["SK"] == f"LANC#{lanc['id']}"


def test_update_mexe_em_atualizado_em(repo):
    lanc = _cria(repo)
    alterado = repo.update("2026-10", lanc["id"], {**BASE, "descricao": "Luz (corrigido)"})
    assert alterado["atualizadoEm"] >= lanc["atualizadoEm"]
    assert alterado["criadoEm"] == lanc["criadoEm"]


def test_update_inexistente_ou_cancelado(repo):
    assert repo.update("2026-10", "nao-existe", BASE) is None
    lanc = _cria(repo)
    repo.soft_delete("2026-10", lanc["id"])
    assert repo.update("2026-10", lanc["id"], BASE) is None


# --- soft delete ----------------------------------------------------------


def test_soft_delete_marca_inativo_sem_apagar(repo, dynamo_table):
    lanc = _cria(repo)
    assert repo.soft_delete("2026-10", lanc["id"]) is True

    item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
    assert item is not None, "histórico financeiro não se apaga"
    assert item["ativo"] is False


def test_soft_delete_repetido(repo):
    lanc = _cria(repo)
    assert repo.soft_delete("2026-10", lanc["id"]) is True
    assert repo.soft_delete("2026-10", lanc["id"]) is False


def test_soft_delete_inexistente(repo):
    assert repo.soft_delete("2026-10", "nao-existe") is False


# --- GSI1 esparso, indexado por COMPETÊNCIA (FIN-12) ----------------------


def test_sem_competencia_fica_fora_do_indice(repo, dynamo_table):
    """Despesa comum e aula avulsa de aluno não são mensalidade — fora do índice."""
    sem_nada = _cria(repo)
    so_paciente = _cria(repo, tipo="entrada", pacienteId="p1", descricao="Aula avulsa")

    for lanc in (sem_nada, so_paciente):
        item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
        assert "GSI1PK" not in item
        assert "GSI1SK" not in item


def test_mensalidade_grava_chaves_do_indice(repo, dynamo_table):
    lanc = _cria(repo, tipo="entrada", pacienteId="p1", competencia="2026-10")
    item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
    assert item["GSI1PK"] == f"CLINIC#{CLINICA}#FIN#COMP#2026-10"
    assert item["GSI1SK"] == f"p1#{lanc['id']}"


def test_list_por_competencia_alcanca_outra_particao_mensal(repo):
    """O ponto da feature: mensalidade de setembro paga em outubro conta em setembro."""
    _cria(repo, tipo="entrada", data="2026-10-03", pacienteId="p1", competencia="2026-09",
          valorCentavos=26000, descricao="Mensalidade setembro (atrasada)")
    _cria(repo, tipo="entrada", data="2026-09-05", pacienteId="p2", competencia="2026-09",
          valorCentavos=34000, descricao="Mensalidade setembro")

    setembro = repo.list_por_competencia("2026-09")
    assert sorted(l["pacienteId"] for l in setembro) == ["p1", "p2"]
    assert sum(l["valorCentavos"] for l in setembro) == 60000
    # E o caixa de cada mês continua contando o dinheiro no mês em que ele andou.
    assert len(repo.list_mes("2026-10")) == 1
    assert len(repo.list_mes("2026-09")) == 1


def test_list_por_competencia_ignora_cancelado(repo):
    lanc = _cria(repo, tipo="entrada", pacienteId="p1", competencia="2026-10")
    _cria(repo, tipo="entrada", pacienteId="p2", competencia="2026-10")
    repo.soft_delete("2026-10", lanc["id"])

    assert [l["pacienteId"] for l in repo.list_por_competencia("2026-10")] == ["p2"]


def test_mesmo_aluno_paga_em_duas_parcelas(repo):
    """O id no fim do GSI1SK é o que permite as duas parcelas coexistirem no índice."""
    _cria(repo, tipo="entrada", pacienteId="p1", competencia="2026-10", valorCentavos=13000)
    _cria(repo, tipo="entrada", pacienteId="p1", competencia="2026-10", valorCentavos=13000)

    pagos = repo.list_por_competencia("2026-10")
    assert len(pagos) == 2
    assert sum(l["valorCentavos"] for l in pagos) == 26000


def test_update_tirando_a_competencia_remove_do_indice(repo, dynamo_table):
    lanc = _cria(repo, tipo="entrada", pacienteId="p1", competencia="2026-10")
    repo.update("2026-10", lanc["id"], {**BASE, "pacienteId": "p1", "competencia": None})

    item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
    assert "GSI1PK" not in item
    assert repo.list_por_competencia("2026-10") == []


def test_update_pondo_a_competencia_entra_no_indice(repo, dynamo_table):
    lanc = _cria(repo)
    repo.update(
        "2026-10",
        lanc["id"],
        {**BASE, "tipo": "entrada", "pacienteId": "p9", "competencia": "2026-10"},
    )
    item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
    assert item["GSI1PK"] == f"CLINIC#{CLINICA}#FIN#COMP#2026-10"
    assert len(repo.list_por_competencia("2026-10")) == 1


# --- isolamento multi-tenant (o teste mais importante do projeto) ---------


def test_outra_clinica_nao_ve_o_caixa(repo, repo_outra):
    _cria(repo)
    assert repo_outra.list_mes("2026-10") == []


def test_outra_clinica_nao_le_lancamento(repo, repo_outra):
    lanc = _cria(repo)
    assert repo_outra.get("2026-10", lanc["id"]) is None


def test_outra_clinica_nao_altera_nem_cancela(repo, repo_outra, dynamo_table):
    lanc = _cria(repo)
    assert repo_outra.update("2026-10", lanc["id"], {**BASE, "valorCentavos": 1}) is None
    assert repo_outra.soft_delete("2026-10", lanc["id"]) is False

    item = _item_bruto(dynamo_table, CLINICA, "2026-10", lanc["id"])
    assert item["ativo"] is True
    assert int(item["valorCentavos"]) == 15000


def test_outra_clinica_nao_ve_os_pagamentos_da_competencia(repo, repo_outra):
    _cria(repo, tipo="entrada", pacienteId="p1", competencia="2026-10")
    assert repo_outra.list_por_competencia("2026-10") == []
