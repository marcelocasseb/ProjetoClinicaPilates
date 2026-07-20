"""Testes dos endpoints de pacientes (PAC-01, PAC-06).

Usa a fixture `dynamo_table` (moto) de conftest.py e o TestClient do FastAPI.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_criar_paciente_retorna_201(dynamo_table):
    resp = client.post("/pacientes", json={"nome": "Maria"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["nome"] == "Maria"
    assert body["ativo"] is True
    assert body["criadoEm"]


def test_criar_sem_nome_retorna_422(dynamo_table):
    resp = client.post("/pacientes", json={"telefone": "119999"})
    assert resp.status_code == 422


def test_criar_nome_vazio_retorna_422(dynamo_table):
    resp = client.post("/pacientes", json={"nome": "   "})
    assert resp.status_code == 422


def test_criar_email_invalido_retorna_422(dynamo_table):
    resp = client.post("/pacientes", json={"nome": "Ana", "email": "invalido"})
    assert resp.status_code == 422


def test_obter_existente_retorna_200(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana"}).json()
    resp = client.get(f"/pacientes/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == criado["id"]


def test_obter_inexistente_retorna_404(dynamo_table):
    resp = client.get("/pacientes/nao-existe")
    assert resp.status_code == 404


def test_fluxo_post_depois_get(dynamo_table):
    criado = client.post(
        "/pacientes", json={"nome": "Maria", "telefone": "119999"}
    ).json()
    obtido = client.get(f"/pacientes/{criado['id']}").json()
    assert obtido["nome"] == "Maria"
    assert obtido["telefone"] == "119999"
