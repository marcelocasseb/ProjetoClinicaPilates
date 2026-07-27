"""Testes do repositório DynamoDB de Sessão/Aula, multi-tenant (SES-02/04/05/07/08/09).

Usa a fixture `dynamo_table` (moto) de conftest.py.
"""
from datetime import datetime, timezone

import boto3

from app.repository import PacienteRepository
from app.repository_avaliacao import AvaliacaoRepository
from app.repository_sessao import SessaoRepository

CLINICA_A = "clinica-a"
CLINICA_B = "clinica-b"
PACIENTE_1 = "paciente-1"
PACIENTE_2 = "paciente-2"


def _repo(clinic_id=CLINICA_A, paciente_id=PACIENTE_1):
    return SessaoRepository(clinic_id=clinic_id, paciente_id=paciente_id)


def _aparelhos():
    return [{"aparelhoId": "a1", "nome": "Reformer", "treinos": ["Força", "Mobilidade"]}]


def test_create_gera_id_e_data_default_hoje(dynamo_table):
    s = _repo().create({"aparelhos": _aparelhos()})
    assert s["id"]
    assert s["pacienteId"] == PACIENTE_1
    assert s["data"] == datetime.now(timezone.utc).date().isoformat()
    assert s["ativo"] is True
    assert s["criadoEm"] and s["atualizadoEm"]
    assert not any(k in s for k in ("PK", "SK"))


def test_create_respeita_data_informada(dynamo_table):
    s = _repo().create({"data": "2026-01-15", "aparelhos": _aparelhos()})
    assert s["data"] == "2026-01-15"


def test_create_grava_com_chave_sob_o_paciente(dynamo_table):
    s = _repo().create({"data": "2026-02-01", "aparelhos": _aparelhos()})
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINICA_A}#CLIENT#{PACIENTE_1}", "SK": f"SESSION#{s['id']}"}
    )["Item"]
    assert item["PK"] == f"CLINIC#{CLINICA_A}#CLIENT#{PACIENTE_1}"
    assert item["SK"] == f"SESSION#{s['id']}"
    assert item["clinicId"] == CLINICA_A
    assert item["pacienteId"] == PACIENTE_1


def test_aparelhos_round_trip_no_create_e_update(dynamo_table):
    repo = _repo()
    criado = repo.create({"aparelhos": _aparelhos(), "profissional": "Ana", "observacao": "ok"})
    lido = repo.get(criado["id"])
    assert lido["aparelhos"][0]["nome"] == "Reformer"
    assert lido["aparelhos"][0]["treinos"] == ["Força", "Mobilidade"]
    assert lido["profissional"] == "Ana"
    assert lido["observacao"] == "ok"
    atualizado = repo.update(
        criado["id"],
        {"aparelhos": [{"aparelhoId": "a2", "nome": "Cadillac", "treinos": ["Abdômen"]}]},
    )
    assert atualizado["aparelhos"][0]["nome"] == "Cadillac"
    assert atualizado["aparelhos"][0]["treinos"] == ["Abdômen"]


def test_get_inexistente_retorna_none(dynamo_table):
    assert _repo().get("nao-existe") is None


def test_list_ordena_por_data_desc(dynamo_table):
    repo = _repo()
    repo.create({"data": "2026-01-10", "aparelhos": _aparelhos()})
    repo.create({"data": "2026-03-20", "aparelhos": _aparelhos()})
    repo.create({"data": "2026-02-15", "aparelhos": _aparelhos()})
    datas = [s["data"] for s in repo.list_ativos()]
    assert datas == ["2026-03-20", "2026-02-15", "2026-01-10"]


def test_list_vazio(dynamo_table):
    assert _repo().list_ativos() == []


def test_list_nao_inclui_perfil_nem_avaliacao(dynamo_table):
    # perfil (SK=PROFILE) e avaliação (SK=AVALIACAO#) ficam sob a mesma PK; não devem
    # aparecer na listagem de aulas
    PacienteRepository(clinic_id=CLINICA_A).create({"nome": "Ana"})
    AvaliacaoRepository(clinic_id=CLINICA_A, paciente_id=PACIENTE_1).create(
        {"queixaPrincipal": "dor"}
    )
    s = _repo().create({"data": "2026-04-01", "aparelhos": _aparelhos()})
    lista = _repo().list_ativos()
    assert [x["id"] for x in lista] == [s["id"]]


def test_update_altera_campos(dynamo_table):
    repo = _repo()
    criado = repo.create({"data": "2026-05-01", "aparelhos": _aparelhos()})
    atualizado = repo.update(
        criado["id"],
        {"data": "2026-05-01", "aparelhos": _aparelhos(), "observacao": "aluno cansado"},
    )
    assert atualizado["observacao"] == "aluno cansado"
    assert atualizado["criadoEm"] == criado["criadoEm"]


def test_update_inexistente_retorna_none(dynamo_table):
    assert _repo().update("nao-existe", {"aparelhos": _aparelhos()}) is None


def test_soft_delete_marca_inativo_e_some(dynamo_table):
    repo = _repo()
    criado = repo.create({"data": "2026-06-01", "aparelhos": _aparelhos()})
    assert repo.soft_delete(criado["id"]) is True
    assert repo.get(criado["id"]) is None
    assert repo.list_ativos() == []
    item = boto3.resource("dynamodb").Table(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINICA_A}#CLIENT#{PACIENTE_1}", "SK": f"SESSION#{criado['id']}"}
    )["Item"]
    assert item["ativo"] is False


def test_soft_delete_inexistente_retorna_false(dynamo_table):
    assert _repo().soft_delete("nao-existe") is False


# --- Isolamento multi-tenant e por paciente (SES-09) ---


def test_pacientes_nao_compartilham_aulas(dynamo_table):
    s1 = _repo(paciente_id=PACIENTE_1).create({"data": "2026-01-01", "aparelhos": _aparelhos()})
    _repo(paciente_id=PACIENTE_2).create({"data": "2026-01-02", "aparelhos": _aparelhos()})
    assert [x["id"] for x in _repo(paciente_id=PACIENTE_1).list_ativos()] == [s1["id"]]
    assert _repo(paciente_id=PACIENTE_2).get(s1["id"]) is None


def test_clinica_b_nao_acessa_aula_da_a(dynamo_table):
    criado_a = _repo(CLINICA_A).create({"data": "2026-01-01", "aparelhos": _aparelhos()})
    assert _repo(CLINICA_B).get(criado_a["id"]) is None
    assert _repo(CLINICA_B).soft_delete(criado_a["id"]) is False
    assert _repo(CLINICA_B).update(criado_a["id"], {"aparelhos": _aparelhos()}) is None
    assert _repo(CLINICA_A).get(criado_a["id"]) is not None
