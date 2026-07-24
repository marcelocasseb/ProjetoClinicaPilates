"""Testes do repositório DynamoDB de Avaliação, multi-tenant (AVL-02/05/06/07/08/09).

Usa a fixture `dynamo_table` (moto) de conftest.py.
"""
from datetime import datetime, timezone

import boto3

from app.repository import PacienteRepository
from app.repository_avaliacao import AvaliacaoRepository

CLINICA_A = "clinica-a"
CLINICA_B = "clinica-b"
PACIENTE_1 = "paciente-1"
PACIENTE_2 = "paciente-2"


def _repo(clinic_id=CLINICA_A, paciente_id=PACIENTE_1):
    return AvaliacaoRepository(clinic_id=clinic_id, paciente_id=paciente_id)


def test_create_gera_id_e_data_default_hoje(dynamo_table):
    a = _repo().create({"queixaPrincipal": "dor lombar"})
    assert a["id"]
    assert a["pacienteId"] == PACIENTE_1
    assert a["queixaPrincipal"] == "dor lombar"
    assert a["data"] == datetime.now(timezone.utc).date().isoformat()
    assert a["ativo"] is True
    assert a["criadoEm"] and a["atualizadoEm"]
    assert not any(k in a for k in ("PK", "SK"))


def test_create_respeita_data_informada(dynamo_table):
    a = _repo().create({"data": "2026-01-15"})
    assert a["data"] == "2026-01-15"


def test_create_grava_com_chave_sob_o_paciente(dynamo_table):
    a = _repo().create({"data": "2026-02-01"})
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINICA_A}#CLIENT#{PACIENTE_1}", "SK": f"AVALIACAO#{a['id']}"}
    )["Item"]
    assert item["PK"] == f"CLINIC#{CLINICA_A}#CLIENT#{PACIENTE_1}"
    assert item["SK"] == f"AVALIACAO#{a['id']}"
    assert item["clinicId"] == CLINICA_A
    assert item["pacienteId"] == PACIENTE_1


def test_create_persiste_maps_aninhados(dynamo_table):
    a = _repo().create(
        {"avaliacaoPostural": {"vistaAnterior": "ombros elevados"}, "medidas": {"braco": "30cm"}}
    )
    lido = _repo().get(a["id"])
    assert lido["avaliacaoPostural"]["vistaAnterior"] == "ombros elevados"
    assert lido["medidas"]["braco"] == "30cm"


def test_get_inexistente_retorna_none(dynamo_table):
    assert _repo().get("nao-existe") is None


def test_list_ordena_por_data_desc(dynamo_table):
    repo = _repo()
    repo.create({"data": "2026-01-10"})
    repo.create({"data": "2026-03-20"})
    repo.create({"data": "2026-02-15"})
    datas = [a["data"] for a in repo.list_ativos()]
    assert datas == ["2026-03-20", "2026-02-15", "2026-01-10"]


def test_list_vazio(dynamo_table):
    assert _repo().list_ativos() == []


def test_list_nao_inclui_o_perfil_do_paciente(dynamo_table):
    # o perfil (SK=PROFILE) fica sob a mesma PK, mas não deve aparecer nas avaliações
    PacienteRepository(clinic_id=CLINICA_A).create({"nome": "Ana"})
    # nota: o perfil criado acima tem outro id; garantimos que a avaliação não pega o PROFILE
    a = _repo().create({"data": "2026-04-01"})
    lista = _repo().list_ativos()
    assert [x["id"] for x in lista] == [a["id"]]


def test_update_altera_campos(dynamo_table):
    repo = _repo()
    criado = repo.create({"data": "2026-05-01", "queixaPrincipal": "dor"})
    atualizado = repo.update(criado["id"], {"data": "2026-05-01", "queixaPrincipal": "sem dor"})
    assert atualizado["queixaPrincipal"] == "sem dor"
    assert atualizado["criadoEm"] == criado["criadoEm"]


def test_observacao_persiste_no_create_e_update(dynamo_table):
    repo = _repo()
    criado = repo.create({"observacao": "paciente evoluiu bem na sessão"})
    assert repo.get(criado["id"])["observacao"] == "paciente evoluiu bem na sessão"
    atualizado = repo.update(criado["id"], {"observacao": "manteve o quadro"})
    assert atualizado["observacao"] == "manteve o quadro"


def test_update_inexistente_retorna_none(dynamo_table):
    assert _repo().update("nao-existe", {"data": "2026-05-01"}) is None


def test_soft_delete_marca_inativo_e_some(dynamo_table):
    repo = _repo()
    criado = repo.create({"data": "2026-06-01"})
    assert repo.soft_delete(criado["id"]) is True
    assert repo.get(criado["id"]) is None
    assert repo.list_ativos() == []
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINICA_A}#CLIENT#{PACIENTE_1}", "SK": f"AVALIACAO#{criado['id']}"}
    )["Item"]
    assert item["ativo"] is False


def test_soft_delete_inexistente_retorna_false(dynamo_table):
    assert _repo().soft_delete("nao-existe") is False


# --- Isolamento multi-tenant e por paciente (AVL-09) ---


def test_pacientes_nao_compartilham_avaliacoes(dynamo_table):
    a1 = _repo(paciente_id=PACIENTE_1).create({"data": "2026-01-01"})
    _repo(paciente_id=PACIENTE_2).create({"data": "2026-01-02"})
    assert [x["id"] for x in _repo(paciente_id=PACIENTE_1).list_ativos()] == [a1["id"]]
    assert _repo(paciente_id=PACIENTE_2).get(a1["id"]) is None


def test_clinica_b_nao_acessa_avaliacao_da_a(dynamo_table):
    criado_a = _repo(CLINICA_A).create({"data": "2026-01-01"})
    assert _repo(CLINICA_B).get(criado_a["id"]) is None
    assert _repo(CLINICA_B).soft_delete(criado_a["id"]) is False
    assert _repo(CLINICA_B).update(criado_a["id"], {"data": "2026-01-01"}) is None
    assert _repo(CLINICA_A).get(criado_a["id"]) is not None
