"""Testes dos endpoints de aparelhos (APR-01/04/05/06/07/08/09)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_criar_aparelho_retorna_201(dynamo_table):
    resp = client.post("/aparelhos", json={"nome": "Reformer", "categoria": "Reformer"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["nome"] == "Reformer"
    assert body["ativo"] is True


def test_criar_sem_nome_retorna_400(dynamo_table):
    resp = client.post("/aparelhos", json={"categoria": "x"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "nome é obrigatório"


def test_obter_existente_retorna_200(dynamo_table):
    criado = client.post("/aparelhos", json={"nome": "Cadillac"}).json()
    resp = client.get(f"/aparelhos/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == criado["id"]


def test_obter_inexistente_retorna_404(dynamo_table):
    resp = client.get("/aparelhos/nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Aparelho não encontrado"


def test_listar_vazio_e_apos_criar(dynamo_table):
    assert client.get("/aparelhos").json() == []
    client.post("/aparelhos", json={"nome": "Reformer"})
    client.post("/aparelhos", json={"nome": "Chair"})
    assert len(client.get("/aparelhos").json()) == 2


def test_editar_retorna_200_e_atualiza(dynamo_table):
    criado = client.post("/aparelhos", json={"nome": "Chair", "categoria": "x"}).json()
    resp = client.put(f"/aparelhos/{criado['id']}", json={"nome": "Chair", "categoria": "Cadeira"})
    assert resp.status_code == 200
    assert resp.json()["categoria"] == "Cadeira"


def test_editar_nome_vazio_retorna_400(dynamo_table):
    criado = client.post("/aparelhos", json={"nome": "Chair"}).json()
    resp = client.put(f"/aparelhos/{criado['id']}", json={"nome": ""})
    assert resp.status_code == 400


def test_remover_retorna_200_e_some(dynamo_table):
    criado = client.post("/aparelhos", json={"nome": "Barrel"}).json()
    resp = client.delete(f"/aparelhos/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Aparelho removido com sucesso"
    assert client.get(f"/aparelhos/{criado['id']}").status_code == 404


def test_remover_inexistente_retorna_404(dynamo_table):
    resp = client.delete("/aparelhos/nao-existe")
    assert resp.status_code == 404


# --- Isolamento multi-tenant por header X-Clinic-Id (APR-08) ---


def test_isolamento_entre_clinicas_via_header(dynamo_table):
    a = {"X-Clinic-Id": "clinica-a"}
    b = {"X-Clinic-Id": "clinica-b"}
    criado_a = client.post("/aparelhos", json={"nome": "Reformer A"}, headers=a).json()
    client.post("/aparelhos", json={"nome": "Cadillac B"}, headers=b)
    assert [x["nome"] for x in client.get("/aparelhos", headers=a).json()] == ["Reformer A"]
    assert [x["nome"] for x in client.get("/aparelhos", headers=b).json()] == ["Cadillac B"]
    assert client.get(f"/aparelhos/{criado_a['id']}", headers=b).status_code == 404
    assert client.get(f"/aparelhos/{criado_a['id']}", headers=a).status_code == 200


def test_health_e_pacientes_seguem_funcionando(dynamo_table):
    # sem regressão nas rotas existentes
    assert client.get("/health").status_code == 200
    assert client.post("/pacientes", json={"nome": "Ana"}).status_code == 201
