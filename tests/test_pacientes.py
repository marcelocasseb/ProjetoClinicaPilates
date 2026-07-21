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


def test_criar_sem_nome_retorna_400_com_mensagem(dynamo_table):
    resp = client.post("/pacientes", json={"telefone": "119999"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "nome é obrigatório"


def test_criar_nome_vazio_retorna_400_com_mensagem(dynamo_table):
    resp = client.post("/pacientes", json={"nome": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "nome é obrigatório"


def test_criar_email_invalido_retorna_400(dynamo_table):
    resp = client.post("/pacientes", json={"nome": "Ana", "email": "invalido"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "email inválido"


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


def test_editar_nome_vazio_retorna_400(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana"}).json()
    resp = client.put(f"/pacientes/{criado['id']}", json={"nome": ""})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "nome é obrigatório"


def test_editar_inexistente_retorna_404(dynamo_table):
    resp = client.put("/pacientes/nao-existe", json={"nome": "X"})
    assert resp.status_code == 404


def test_remover_retorna_200_com_mensagem_e_some_do_get(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana"}).json()
    resp = client.delete(f"/pacientes/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Paciente removido com sucesso"
    assert client.get(f"/pacientes/{criado['id']}").status_code == 404


def test_removido_some_da_listagem(dynamo_table):
    a = client.post("/pacientes", json={"nome": "A"}).json()
    client.post("/pacientes", json={"nome": "B"})
    client.delete(f"/pacientes/{a['id']}")
    nomes = [p["nome"] for p in client.get("/pacientes").json()]
    assert nomes == ["B"]


def test_remover_inexistente_retorna_404_com_mensagem(dynamo_table):
    resp = client.delete("/pacientes/nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Paciente não encontrado"


def test_editar_removido_retorna_404(dynamo_table):
    criado = client.post("/pacientes", json={"nome": "Ana"}).json()
    client.delete(f"/pacientes/{criado['id']}")
    resp = client.put(f"/pacientes/{criado['id']}", json={"nome": "Ana Maria"})
    assert resp.status_code == 404


# --- CPF + endereço via API (AD-008, AD-009) ---


def test_criar_com_cpf_e_endereco_via_api(dynamo_table):
    payload = {
        "nome": "Maria",
        "cpf": "529.982.247-25",
        "endereco": {
            "cep": "01310-100",
            "logradouro": "Av. Paulista",
            "numero": "1000",
            "bairro": "Bela Vista",
            "cidade": "São Paulo",
            "uf": "SP",
        },
    }
    criado = client.post("/pacientes", json=payload).json()
    assert criado["cpf"] == "52998224725"
    assert criado["endereco"]["cep"] == "01310100"
    obtido = client.get(f"/pacientes/{criado['id']}").json()
    assert obtido["endereco"]["cidade"] == "São Paulo"


def test_criar_cpf_invalido_retorna_400(dynamo_table):
    resp = client.post("/pacientes", json={"nome": "Ana", "cpf": "12345678900"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "CPF inválido"


# --- Isolamento multi-tenant por header X-Clinic-Id (AD-007) ---


def test_isolamento_entre_clinicas_via_header(dynamo_table):
    a = {"X-Clinic-Id": "clinica-a"}
    b = {"X-Clinic-Id": "clinica-b"}
    criado_a = client.post("/pacientes", json={"nome": "Paciente A"}, headers=a).json()
    client.post("/pacientes", json={"nome": "Paciente B"}, headers=b)
    # cada clínica só lista o seu
    assert [p["nome"] for p in client.get("/pacientes", headers=a).json()] == ["Paciente A"]
    assert [p["nome"] for p in client.get("/pacientes", headers=b).json()] == ["Paciente B"]
    # clínica B não acessa o paciente da A por id
    assert client.get(f"/pacientes/{criado_a['id']}", headers=b).status_code == 404
    assert client.get(f"/pacientes/{criado_a['id']}", headers=a).status_code == 200
