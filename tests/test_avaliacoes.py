"""Testes dos endpoints de avaliações (AVL-01/04/05/06/07/08/09)."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _cria_paciente(nome="Ana", headers=None):
    return client.post("/pacientes", json={"nome": nome}, headers=headers or {}).json()["id"]


def _base(paciente_id):
    return f"/pacientes/{paciente_id}/avaliacoes"


def test_criar_avaliacao_retorna_201_e_data_hoje(dynamo_table):
    pid = _cria_paciente()
    resp = client.post(_base(pid), json={"queixaPrincipal": "dor lombar"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["pacienteId"] == pid
    assert body["queixaPrincipal"] == "dor lombar"
    assert body["data"] == datetime.now(timezone.utc).date().isoformat()
    assert body["ativo"] is True


def test_criar_para_paciente_inexistente_retorna_404(dynamo_table):
    resp = client.post(_base("nao-existe"), json={"queixaPrincipal": "x"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Paciente não encontrado"


def test_criar_com_data_invalida_retorna_400(dynamo_table):
    pid = _cria_paciente()
    resp = client.post(_base(pid), json={"data": "22-07-2026"})
    assert resp.status_code == 400


def test_obter_existente_retorna_200(dynamo_table):
    pid = _cria_paciente()
    criado = client.post(_base(pid), json={"data": "2026-03-01"}).json()
    resp = client.get(f"{_base(pid)}/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == criado["id"]


def test_obter_inexistente_retorna_404(dynamo_table):
    pid = _cria_paciente()
    resp = client.get(f"{_base(pid)}/nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Avaliação não encontrada"


def test_listar_vazio_e_ordenado_desc(dynamo_table):
    pid = _cria_paciente()
    assert client.get(_base(pid)).json() == []
    client.post(_base(pid), json={"data": "2026-01-10"})
    client.post(_base(pid), json={"data": "2026-03-20"})
    datas = [a["data"] for a in client.get(_base(pid)).json()]
    assert datas == ["2026-03-20", "2026-01-10"]


def test_editar_retorna_200_e_atualiza(dynamo_table):
    pid = _cria_paciente()
    criado = client.post(_base(pid), json={"data": "2026-05-01", "queixaPrincipal": "dor"}).json()
    resp = client.put(
        f"{_base(pid)}/{criado['id']}", json={"data": "2026-05-01", "queixaPrincipal": "sem dor"}
    )
    assert resp.status_code == 200
    assert resp.json()["queixaPrincipal"] == "sem dor"


def test_remover_retorna_200_e_some(dynamo_table):
    pid = _cria_paciente()
    criado = client.post(_base(pid), json={"data": "2026-06-01"}).json()
    resp = client.delete(f"{_base(pid)}/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Avaliação removida com sucesso"
    assert client.get(f"{_base(pid)}/{criado['id']}").status_code == 404


def test_remover_inexistente_retorna_404(dynamo_table):
    pid = _cria_paciente()
    assert client.delete(f"{_base(pid)}/nao-existe").status_code == 404


def test_maps_aninhados_persistem_via_api(dynamo_table):
    pid = _cria_paciente()
    payload = {
        "avaliacaoPostural": {"vistaAnterior": "ombros elevados"},
        "medidas": {"braco": "30cm", "coxa": "50cm"},
    }
    criado = client.post(_base(pid), json=payload).json()
    lido = client.get(f"{_base(pid)}/{criado['id']}").json()
    assert lido["avaliacaoPostural"]["vistaAnterior"] == "ombros elevados"
    assert lido["medidas"]["coxa"] == "50cm"


# --- Isolamento multi-tenant por header X-Clinic-Id (AVL-09) ---


def test_isolamento_entre_clinicas_via_header(dynamo_table):
    a = {"X-Clinic-Id": "clinica-a"}
    b = {"X-Clinic-Id": "clinica-b"}
    pid_a = _cria_paciente("Paciente A", headers=a)
    criado_a = client.post(_base(pid_a), json={"data": "2026-01-01"}, headers=a).json()
    # clínica B não enxerga o paciente de A (paciente inexistente na sua clínica → 404)
    assert client.get(_base(pid_a), headers=b).status_code == 404
    assert client.get(f"{_base(pid_a)}/{criado_a['id']}", headers=b).status_code == 404
    # clínica A continua acessando normalmente
    assert client.get(f"{_base(pid_a)}/{criado_a['id']}", headers=a).status_code == 200


def test_rotas_existentes_sem_regressao(dynamo_table):
    assert client.get("/health").status_code == 200
    assert client.post("/pacientes", json={"nome": "Bia"}).status_code == 201
    assert client.post("/aparelhos", json={"nome": "Reformer"}).status_code == 201
