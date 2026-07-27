"""Testes dos endpoints de sessões/aulas (SES-01/04/05/06/07/08/09)."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _cria_paciente(nome="Ana", headers=None):
    return client.post("/pacientes", json={"nome": nome}, headers=headers or {}).json()["id"]


def _base(paciente_id):
    return f"/pacientes/{paciente_id}/sessoes"


def _aparelhos():
    return [{"aparelhoId": "a1", "nome": "Reformer", "treinos": ["Força", "Mobilidade"]}]


def test_criar_aula_retorna_201_e_data_hoje(dynamo_table):
    pid = _cria_paciente()
    resp = client.post(_base(pid), json={"aparelhos": _aparelhos()})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["pacienteId"] == pid
    assert body["aparelhos"][0]["nome"] == "Reformer"
    assert body["aparelhos"][0]["treinos"] == ["Força", "Mobilidade"]
    assert body["data"] == datetime.now(timezone.utc).date().isoformat()
    assert body["ativo"] is True


def test_criar_sem_aparelho_retorna_400(dynamo_table):
    pid = _cria_paciente()
    resp = client.post(_base(pid), json={"aparelhos": []})
    assert resp.status_code == 400
    assert "aparelho" in resp.json()["detail"].lower()


def test_criar_para_paciente_inexistente_retorna_404(dynamo_table):
    resp = client.post(_base("nao-existe"), json={"aparelhos": _aparelhos()})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Paciente não encontrado"


def test_criar_com_data_invalida_retorna_400(dynamo_table):
    pid = _cria_paciente()
    resp = client.post(_base(pid), json={"data": "27-07-2026", "aparelhos": _aparelhos()})
    assert resp.status_code == 400


def test_obter_existente_retorna_200(dynamo_table):
    pid = _cria_paciente()
    criado = client.post(_base(pid), json={"data": "2026-03-01", "aparelhos": _aparelhos()}).json()
    resp = client.get(f"{_base(pid)}/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == criado["id"]


def test_obter_inexistente_retorna_404(dynamo_table):
    pid = _cria_paciente()
    resp = client.get(f"{_base(pid)}/nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Aula não encontrada"


def test_listar_vazio_e_ordenado_desc(dynamo_table):
    pid = _cria_paciente()
    assert client.get(_base(pid)).json() == []
    client.post(_base(pid), json={"data": "2026-01-10", "aparelhos": _aparelhos()})
    client.post(_base(pid), json={"data": "2026-03-20", "aparelhos": _aparelhos()})
    datas = [s["data"] for s in client.get(_base(pid)).json()]
    assert datas == ["2026-03-20", "2026-01-10"]


def test_editar_retorna_200_e_atualiza(dynamo_table):
    pid = _cria_paciente()
    criado = client.post(_base(pid), json={"data": "2026-05-01", "aparelhos": _aparelhos()}).json()
    resp = client.put(
        f"{_base(pid)}/{criado['id']}",
        json={
            "data": "2026-05-01",
            "aparelhos": [{"aparelhoId": "a2", "nome": "Cadillac", "treinos": ["Abdômen"]}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["aparelhos"][0]["nome"] == "Cadillac"


def test_editar_sem_aparelho_retorna_400(dynamo_table):
    pid = _cria_paciente()
    criado = client.post(_base(pid), json={"data": "2026-05-01", "aparelhos": _aparelhos()}).json()
    resp = client.put(f"{_base(pid)}/{criado['id']}", json={"aparelhos": []})
    assert resp.status_code == 400


def test_remover_retorna_200_e_some(dynamo_table):
    pid = _cria_paciente()
    criado = client.post(_base(pid), json={"data": "2026-06-01", "aparelhos": _aparelhos()}).json()
    resp = client.delete(f"{_base(pid)}/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Aula removida com sucesso"
    assert client.get(f"{_base(pid)}/{criado['id']}").status_code == 404


def test_remover_inexistente_retorna_404(dynamo_table):
    pid = _cria_paciente()
    assert client.delete(f"{_base(pid)}/nao-existe").status_code == 404


def test_aparelhos_persistem_via_api(dynamo_table):
    pid = _cria_paciente()
    payload = {
        "profissional": "Ana",
        "observacao": "aluno evoluindo",
        "aparelhos": [
            {"aparelhoId": "a1", "nome": "Reformer", "treinos": ["Força"]},
            {"aparelhoId": "a2", "nome": "Cadillac", "treinos": ["Mobilidade", "Abdômen"]},
        ],
    }
    criado = client.post(_base(pid), json=payload).json()
    lido = client.get(f"{_base(pid)}/{criado['id']}").json()
    assert lido["profissional"] == "Ana"
    assert len(lido["aparelhos"]) == 2
    assert lido["aparelhos"][1]["treinos"] == ["Mobilidade", "Abdômen"]


# --- Isolamento multi-tenant por header X-Clinic-Id (SES-09) ---


def test_isolamento_entre_clinicas_via_header(dynamo_table):
    a = {"X-Clinic-Id": "clinica-a"}
    b = {"X-Clinic-Id": "clinica-b"}
    pid_a = _cria_paciente("Paciente A", headers=a)
    criado_a = client.post(_base(pid_a), json={"data": "2026-01-01", "aparelhos": _aparelhos()}, headers=a).json()
    # clínica B não enxerga o paciente de A (paciente inexistente na sua clínica → 404)
    assert client.get(_base(pid_a), headers=b).status_code == 404
    assert client.get(f"{_base(pid_a)}/{criado_a['id']}", headers=b).status_code == 404
    # clínica A continua acessando normalmente
    assert client.get(f"{_base(pid_a)}/{criado_a['id']}", headers=a).status_code == 200


def test_rotas_existentes_sem_regressao(dynamo_table):
    assert client.get("/health").status_code == 200
    assert client.post("/pacientes", json={"nome": "Bia"}).status_code == 201
    assert client.post("/aparelhos", json={"nome": "Reformer"}).status_code == 201
    pid = _cria_paciente()
    assert client.post(_base(pid).replace("/sessoes", "/avaliacoes"), json={"queixaPrincipal": "x"}).status_code == 201
