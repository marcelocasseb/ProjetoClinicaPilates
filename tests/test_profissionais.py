"""Testes do cadastro de Profissionais e do profissional na Agenda."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OUTRA = {"X-Clinic-Id": "clinica-corpo"}


def _prof(nome="Dra. Ana", headers=None, **extra):
    return client.post("/profissionais", json={"nome": nome, **extra}, headers=headers or {})


def _agendar(**dados):
    return client.post("/agenda", json={"data": "2026-10-19", "hora": "07:00", **dados})


def _listar_agenda():
    return client.get("/agenda?de=2026-10-19&ate=2026-10-25").json()


# --- Cadastro ---


def test_criar_e_listar_em_ordem_alfabetica(dynamo_table):
    assert _prof("Paula", telefone=" (91) 98888-0000 ").status_code == 201
    assert _prof("ana").status_code == 201
    lista = client.get("/profissionais").json()
    assert [p["nome"] for p in lista] == ["Ana", "Paula"]
    assert lista[1]["telefone"] == "(91) 98888-0000"


def test_nome_obrigatorio(dynamo_table):
    resp = _prof("   ")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "nome é obrigatório"


def test_editar(dynamo_table):
    pid = _prof().json()["id"]
    resp = client.put(f"/profissionais/{pid}", json={"nome": "Dra. Ana Lima", "telefone": ""})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Dra. Ana Lima"
    assert resp.json()["telefone"] is None


def test_remover_some_da_lista(dynamo_table):
    pid = _prof().json()["id"]
    assert client.delete(f"/profissionais/{pid}").status_code == 200
    assert client.get("/profissionais").json() == []
    assert client.delete(f"/profissionais/{pid}").status_code == 404
    assert client.put(f"/profissionais/{pid}", json={"nome": "X"}).status_code == 404


def test_isolado_por_clinica(dynamo_table):
    pid = _prof().json()["id"]
    assert client.get("/profissionais", headers=OUTRA).json() == []
    assert client.delete(f"/profissionais/{pid}", headers=OUTRA).status_code == 404


# --- Profissional na Agenda ---


def test_agendar_com_profissional(dynamo_table):
    pid = _prof().json()["id"]
    body = _agendar(nome="João", profissionalId=pid).json()
    assert body["profissionalId"] == pid
    assert body["profissional"] == "Dra. Ana"
    assert _listar_agenda()[0]["profissional"] == "Dra. Ana"


def test_agendar_sem_profissional(dynamo_table):
    body = _agendar(nome="João", profissionalId="").json()
    assert body["profissionalId"] is None
    assert body["profissional"] is None


def test_agendar_com_profissional_inexistente_retorna_404(dynamo_table):
    resp = _agendar(nome="João", profissionalId="nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Profissional não encontrado"
    assert _listar_agenda() == []


def test_mesmo_profissional_duas_pessoas_no_horario_e_permitido(dynamo_table):
    """Atendimento em grupo: o aviso é da tela, o backend não bloqueia."""
    pid = _prof().json()["id"]
    assert _agendar(nome="João", profissionalId=pid).status_code == 201
    assert _agendar(nome="Maria", profissionalId=pid).status_code == 201


def test_nome_do_profissional_ao_vivo_e_mantido_apos_remocao(dynamo_table):
    pid = _prof().json()["id"]
    _agendar(nome="João", profissionalId=pid)
    client.put(f"/profissionais/{pid}", json={"nome": "Dra. Ana Lima"})
    assert _listar_agenda()[0]["profissional"] == "Dra. Ana Lima"
    client.delete(f"/profissionais/{pid}")
    assert _listar_agenda()[0]["profissional"] == "Dra. Ana Lima"


def test_definir_trocar_e_tirar_profissional(dynamo_table):
    ana = _prof().json()["id"]
    bia = _prof("Bia").json()["id"]
    ag = _agendar(nome="João").json()
    url = f"/agenda/{ag['data']}/07%3A00/{ag['id']}/profissional"

    assert client.put(url, json={"profissionalId": ana}).json()["profissional"] == "Dra. Ana"
    assert client.put(url, json={"profissionalId": bia}).json()["profissional"] == "Bia"
    resp = client.put(url, json={"profissionalId": None})
    assert resp.status_code == 200
    assert resp.json()["profissional"] is None
    assert _listar_agenda()[0]["profissionalId"] is None


def test_definir_profissional_inexistente_ou_marcacao_inexistente(dynamo_table):
    ag = _agendar(nome="João").json()
    url = f"/agenda/{ag['data']}/07%3A00/{ag['id']}/profissional"
    assert client.put(url, json={"profissionalId": "nao-existe"}).status_code == 404
    ana = _prof().json()["id"]
    resp = client.put(f"/agenda/2026-10-19/07%3A00/nao-existe/profissional", json={"profissionalId": ana})
    assert resp.status_code == 404
    # não pode ter criado item fantasma
    assert len(_listar_agenda()) == 1
