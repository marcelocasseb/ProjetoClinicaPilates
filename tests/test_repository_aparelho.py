"""Testes do repositório DynamoDB de Aparelho, multi-tenant (APR-02/04/05/07/08).

Usa a fixture `dynamo_table` (moto) de conftest.py.
"""
import boto3

from app.repository import PacienteRepository
from app.repository_aparelho import AparelhoRepository

CLINICA_A = "clinica-a"
CLINICA_B = "clinica-b"


def _repo(clinic_id=CLINICA_A):
    return AparelhoRepository(clinic_id=clinic_id)


def test_create_gera_id_e_persiste(dynamo_table):
    a = _repo().create({"nome": "Reformer", "categoria": "Reformer"})
    assert a["id"]
    assert a["nome"] == "Reformer"
    assert a["categoria"] == "Reformer"
    assert a["ativo"] is True
    assert a["criadoEm"] and a["atualizadoEm"]
    assert not any(k in a for k in ("PK", "SK"))


def test_create_grava_com_chave_nivel_clinica(dynamo_table):
    a = _repo().create({"nome": "Cadillac"})
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINICA_A}", "SK": f"APARELHO#{a['id']}"}
    )["Item"]
    assert item["PK"] == f"CLINIC#{CLINICA_A}"
    assert item["SK"] == f"APARELHO#{a['id']}"
    assert item["clinicId"] == CLINICA_A


def test_get_retorna_ativo(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Chair"})
    assert repo.get(criado["id"])["id"] == criado["id"]


def test_get_inexistente_retorna_none(dynamo_table):
    assert _repo().get("nao-existe") is None


def test_list_retorna_ativos(dynamo_table):
    repo = _repo()
    repo.create({"nome": "Reformer"})
    repo.create({"nome": "Cadillac"})
    assert len(repo.list_ativos()) == 2


def test_list_vazio(dynamo_table):
    assert _repo().list_ativos() == []


def test_update_altera_campos(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Chair", "categoria": "x"})
    atualizado = repo.update(criado["id"], {"nome": "Chair", "categoria": "Cadeira"})
    assert atualizado["categoria"] == "Cadeira"
    assert atualizado["criadoEm"] == criado["criadoEm"]


def test_update_inexistente_retorna_none(dynamo_table):
    assert _repo().update("nao-existe", {"nome": "X"}) is None


def test_soft_delete_marca_inativo_e_get_none(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Barrel"})
    assert repo.soft_delete(criado["id"]) is True
    assert repo.get(criado["id"]) is None


def test_soft_delete_item_permanece_na_tabela(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Barrel"})
    repo.soft_delete(criado["id"])
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINICA_A}", "SK": f"APARELHO#{criado['id']}"}
    )["Item"]
    assert item["ativo"] is False


def test_soft_delete_inexistente_retorna_false(dynamo_table):
    assert _repo().soft_delete("nao-existe") is False


def test_list_omite_removidos(dynamo_table):
    repo = _repo()
    a = repo.create({"nome": "Reformer"})
    repo.create({"nome": "Cadillac"})
    repo.soft_delete(a["id"])
    ativos = repo.list_ativos()
    assert len(ativos) == 1
    assert ativos[0]["nome"] == "Cadillac"


def test_list_nao_inclui_pacientes_da_mesma_clinica(dynamo_table):
    # aparelhos e pacientes coexistem na mesma tabela sob a mesma clínica
    PacienteRepository(clinic_id=CLINICA_A).create({"nome": "Paciente X"})
    _repo().create({"nome": "Reformer"})
    aparelhos = _repo().list_ativos()
    assert [a["nome"] for a in aparelhos] == ["Reformer"]


# --- Isolamento entre clínicas (APR-08) ---


def test_clinicas_nao_veem_aparelhos_uma_da_outra(dynamo_table):
    _repo(CLINICA_A).create({"nome": "Reformer da A"})
    _repo(CLINICA_B).create({"nome": "Cadillac da B"})
    assert [a["nome"] for a in _repo(CLINICA_A).list_ativos()] == ["Reformer da A"]
    assert [a["nome"] for a in _repo(CLINICA_B).list_ativos()] == ["Cadillac da B"]


def test_clinica_b_nao_acessa_aparelho_da_a_por_id(dynamo_table):
    criado_a = _repo(CLINICA_A).create({"nome": "Só da A"})
    assert _repo(CLINICA_B).get(criado_a["id"]) is None
    assert _repo(CLINICA_B).soft_delete(criado_a["id"]) is False
    assert _repo(CLINICA_B).update(criado_a["id"], {"nome": "Hack"}) is None
    assert _repo(CLINICA_A).get(criado_a["id"]) is not None
