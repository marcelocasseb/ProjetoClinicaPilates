"""Testes do repositório DynamoDB de Paciente, multi-tenant (PAC-02/05/06/08; AD-007).

Usa a fixture `dynamo_table` (moto, com GSI1) de conftest.py.
"""
import boto3

from app.repository import PacienteRepository

CLINICA_A = "clinica-a"
CLINICA_B = "clinica-b"


def _repo(clinic_id=CLINICA_A):
    return PacienteRepository(clinic_id=clinic_id)


def test_create_gera_id_e_persiste_perfil(dynamo_table):
    p = _repo().create({"nome": "Maria", "telefone": "119999", "cpf": "52998224725"})
    assert p["id"]
    assert p["nome"] == "Maria"
    assert p["telefone"] == "119999"
    assert p["cpf"] == "52998224725"
    assert p["ativo"] is True
    assert p["criadoEm"] and p["atualizadoEm"]
    assert not any(k in p for k in ("PK", "SK", "GSI1PK", "GSI1SK"))


def test_create_grava_com_chave_multitenant(dynamo_table):
    p = _repo().create({"nome": "Maria"})
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINICA_A}#CLIENT#{p['id']}", "SK": "PROFILE"}
    )["Item"]
    assert item["PK"] == f"CLINIC#{CLINICA_A}#CLIENT#{p['id']}"
    assert item["SK"] == "PROFILE"
    assert item["GSI1PK"] == f"CLINIC#{CLINICA_A}"
    assert item["clinicId"] == CLINICA_A


def test_create_persiste_endereco_map(dynamo_table):
    endereco = {"cep": "01310100", "logradouro": "Av. Paulista", "cidade": "São Paulo", "uf": "SP"}
    p = _repo().create({"nome": "Ana", "endereco": endereco})
    obtido = _repo().get(p["id"])
    assert obtido["endereco"]["cep"] == "01310100"
    assert obtido["endereco"]["cidade"] == "São Paulo"


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
        Key={"PK": f"CLINIC#{CLINICA_A}#CLIENT#{criado['id']}", "SK": "PROFILE"}
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


# --- Isolamento entre clínicas (AD-007) ---


def test_clinicas_nao_veem_pacientes_uma_da_outra(dynamo_table):
    repo_a = _repo(CLINICA_A)
    repo_b = _repo(CLINICA_B)
    repo_a.create({"nome": "Paciente da A"})
    repo_b.create({"nome": "Paciente da B"})
    nomes_a = [p["nome"] for p in repo_a.list_ativos()]
    nomes_b = [p["nome"] for p in repo_b.list_ativos()]
    assert nomes_a == ["Paciente da A"]
    assert nomes_b == ["Paciente da B"]


def test_clinica_b_nao_acessa_paciente_da_a_por_id(dynamo_table):
    criado_a = _repo(CLINICA_A).create({"nome": "Da Clínica A"})
    # mesmo id, mas outra clínica → não encontra
    assert _repo(CLINICA_B).get(criado_a["id"]) is None
    assert _repo(CLINICA_B).soft_delete(criado_a["id"]) is False
    assert _repo(CLINICA_B).update(criado_a["id"], {"nome": "Hack"}) is None
    # a clínica dona continua acessando
    assert _repo(CLINICA_A).get(criado_a["id"]) is not None
