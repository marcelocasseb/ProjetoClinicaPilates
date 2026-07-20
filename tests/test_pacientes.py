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


# --- T4: listar, editar, remover (PAC-05, PAC-07, PAC-08) ---


def test_listar_vazio_retorna_lista_vazia(dynamo_table):
    resp = client.get("/pacientes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_listar_retorna_ativos(dynamo_table):
    client.post("/pacientes", json={"nome": "A"})
    client.post("/pacientes", json={"nome": "B"})
    resp = client.get("/pacientes")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_editar_retorna_200_e_atualiza(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana", "telefone": "111"}).json()
    resp = client.put(f"/pacientes/{criado['id']}", json={"nome": "Ana", "telefone": "222"})
    assert resp.status_code == 200
    assert resp.json()["telefone"] == "222"
    # muda refletida num GET subsequente
    assert client.get(f"/pacientes/{criado['id']}").json()["telefone"] == "222"


def test_editar_nome_vazio_retorna_422(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana"}).json()
    resp = client.put(f"/pacientes/{criado['id']}", json={"nome": ""})
    assert resp.status_code == 422


def test_editar_inexistente_retorna_404(dynamo_table):
    resp = client.put("/pacientes/nao-existe", json={"nome": "X"})
    assert resp.status_code == 404


def test_remover_retorna_204_e_some_do_get(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana"}).json()
    resp = client.delete(f"/pacientes/{criado['id']}")
    assert resp.status_code == 204
    assert client.get(f"/pacientes/{criado['id']}").status_code == 404


def test_removido_some_da_listagem(dynamo_table):
    a = client.post("/pacientes", json={"nome": "A"}).json()
    client.post("/pacientes", json={"nome": "B"})
    client.delete(f"/pacientes/{a['id']}")
    nomes = [p["nome"] for p in client.get("/pacientes").json()]
    assert nomes == ["B"]


def test_remover_inexistente_retorna_404(dynamo_table):
    assert client.delete("/pacientes/nao-existe").status_code == 404


def test_editar_removido_retorna_404(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana"}).json()
    client.delete(f"/pacientes/{criado['id']}")
    resp = client.put(f"/pacientes/{criado['id']}", json={"nome": "Ana Maria"})
    assert resp.status_code == 404
