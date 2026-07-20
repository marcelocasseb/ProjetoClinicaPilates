"""Testes do repositório DynamoDB de Paciente (PAC-02, PAC-05, PAC-06, PAC-08).

Usa a fixture `dynamo_table` (moto) de conftest.py.
"""
import boto3

from app.repository import PacienteRepository


def _repo():
    return PacienteRepository()


def test_create_gera_id_e_persiste_perfil(dynamo_table):
    p = _repo().create({"nome": "Maria", "telefone": "119999"})
    assert p["id"]
    assert p["nome"] == "Maria"
    assert p["telefone"] == "119999"
    assert p["ativo"] is True
    assert p["criadoEm"] and p["atualizadoEm"]
    assert "PK" not in p and "SK" not in p


def test_create_grava_com_pk_sk_da_convencao(dynamo_table):
    p = _repo().create({"nome": "Maria"})
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLIENT#{p['id']}", "SK": "PROFILE"}
    )["Item"]
    assert item["PK"] == f"CLIENT#{p['id']}"
    assert item["SK"] == "PROFILE"


def test_get_retorna_ativo(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Ana"})
    obtido = repo.get(criado["id"])
    assert obtido is not None
    assert obtido["id"] == criado["id"]


def test_get_inexistente_retorna_none(dynamo_table):
    assert _repo().get("nao-existe") is None


def test_list_ativos_retorna_todos(dynamo_table):
    repo = _repo()
    repo.create({"nome": "A"})
    repo.create({"nome": "B"})
    assert len(repo.list_ativos()) == 2


def test_list_vazio(dynamo_table):
    assert _repo().list_ativos() == []


def test_update_altera_campos_e_atualizadoEm(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Ana", "telefone": "111"})
    atualizado = repo.update(criado["id"], {"nome": "Ana", "telefone": "222"})
    assert atualizado["telefone"] == "222"
    assert atualizado["criadoEm"] == criado["criadoEm"]
    assert "atualizadoEm" in atualizado


def test_update_inexistente_retorna_none(dynamo_table):
    assert _repo().update("nao-existe", {"nome": "X"}) is None


def test_soft_delete_marca_inativo_e_get_none(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Ana"})
    assert repo.soft_delete(criado["id"]) is True
    assert repo.get(criado["id"]) is None


def test_soft_delete_item_permanece_na_tabela(dynamo_table):
    repo = _repo()
    criado = repo.create({"nome": "Ana"})
    repo.soft_delete(criado["id"])
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLIENT#{criado['id']}", "SK": "PROFILE"}
    )["Item"]
    assert item["ativo"] is False


def test_soft_delete_inexistente_retorna_false(dynamo_table):
    assert _repo().soft_delete("nao-existe") is False


def test_list_omite_removidos(dynamo_table):
    repo = _repo()
    a = repo.create({"nome": "A"})
    repo.create({"nome": "B"})
    repo.soft_delete(a["id"])
    ativos = repo.list_ativos()
    assert len(ativos) == 1
    assert ativos[0]["nome"] == "B"
