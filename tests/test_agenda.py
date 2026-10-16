"""Testes dos endpoints da Agenda (marcações datadas, feature agenda)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OUTRA = {"X-Clinic-Id": "clinica-corpo"}


def _aluno(nome="Rebecca", headers=None, **extra):
    return client.post("/pacientes", json={"nome": nome, **extra}, headers=headers or {}).json()["id"]


def _agendar(headers=None, **dados):
    corpo = {"data": "2026-10-19", "hora": "07:00", **dados}
    return client.post("/agenda", json=corpo, headers=headers or {})


def _listar(de="2026-10-19", ate="2026-10-25", headers=None):
    return client.get(f"/agenda?de={de}&ate={ate}", headers=headers or {})


# --- Agendar paciente cadastrado ---


def test_agendar_paciente_retorna_201(dynamo_table):
    pid = _aluno(telefone="(91) 99999-0000")
    resp = _agendar(pacienteId=pid)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["data"] == "2026-10-19"
    assert body["hora"] == "07:00"
    assert body["nome"] == "Rebecca"
    assert body["telefone"] == "(91) 99999-0000"
    assert body["novo"] is False


def test_agendar_paciente_inexistente_retorna_404(dynamo_table):
    resp = _agendar(pacienteId="nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Aluno não encontrado"


def test_agendar_paciente_duplicado_retorna_409(dynamo_table):
    pid = _aluno()
    assert _agendar(pacienteId=pid).status_code == 201
    resp = _agendar(pacienteId=pid)
    assert resp.status_code == 409
    assert len(_listar().json()) == 1


def test_mesmo_paciente_em_outra_data_ou_hora(dynamo_table):
    pid = _aluno()
    assert _agendar(pacienteId=pid).status_code == 201
    assert _agendar(pacienteId=pid, hora="08:00").status_code == 201
    assert _agendar(pacienteId=pid, data="2026-10-20").status_code == 201
    assert len(_listar().json()) == 3


# --- Agendar pessoa sem cadastro ---


def test_agendar_pessoa_nova(dynamo_table):
    resp = _agendar(nome="  João Experimental ", telefone="91 98888-7777")
    assert resp.status_code == 201
    body = resp.json()
    assert body["nome"] == "João Experimental"
    assert body["telefone"] == "91 98888-7777"
    assert body["novo"] is True
    assert body["pacienteId"] is None


def test_duas_pessoas_novas_no_mesmo_horario(dynamo_table):
    assert _agendar(nome="Ana").status_code == 201
    assert _agendar(nome="Bia").status_code == 201
    assert len(_listar().json()) == 2


def test_sem_paciente_e_sem_nome_retorna_400(dynamo_table):
    resp = _agendar(nome="   ")
    assert resp.status_code == 400
    assert "nome" in resp.json()["detail"]


def test_paciente_e_nome_juntos_retorna_400(dynamo_table):
    resp = _agendar(pacienteId=_aluno(), nome="Outro")
    assert resp.status_code == 400


# --- Validação de data/hora ---


def test_data_invalida_retorna_400(dynamo_table):
    assert _agendar(nome="Ana", data="2026-02-30").status_code == 400
    assert _agendar(nome="Ana", data="19/10/2026").status_code == 400


def test_hora_invalida_retorna_400(dynamo_table):
    assert _agendar(nome="Ana", hora="7:00").status_code == 400


# --- Listar ---


def test_listar_filtra_periodo_e_ordena(dynamo_table):
    _agendar(nome="Fora antes", data="2026-10-18")
    _agendar(nome="Zé", data="2026-10-20", hora="09:00")
    _agendar(nome="Ana", data="2026-10-20", hora="09:00")
    _agendar(nome="Cedo", data="2026-10-19", hora="06:00")
    _agendar(nome="Último dia", data="2026-10-25", hora="21:00")
    _agendar(nome="Fora depois", data="2026-10-26")
    nomes = [a["nome"] for a in _listar().json()]
    assert nomes == ["Cedo", "Ana", "Zé", "Último dia"]


def test_listar_usa_nome_ao_vivo_e_omite_removidos(dynamo_table):
    pid = _aluno()
    removido = _aluno("Saiu")
    _agendar(pacienteId=pid)
    _agendar(pacienteId=removido)
    client.put(f"/pacientes/{pid}", json={"nome": "Rebecca Lima"})
    client.delete(f"/pacientes/{removido}")
    nomes = [a["nome"] for a in _listar().json()]
    assert nomes == ["Rebecca Lima"]


def test_listar_periodo_invalido_retorna_400(dynamo_table):
    assert _listar(de="2026-10-25", ate="2026-10-19").status_code == 400
    assert _listar(de="2026-01-01", ate="2026-12-31").status_code == 400
    assert _listar(de="ontem").status_code == 400


def test_listar_isolado_por_clinica(dynamo_table):
    _agendar(nome="Ana")
    assert _listar(headers=OUTRA).json() == []


# --- Vincular pessoa nova a paciente ---


def test_vincular_pessoa_nova(dynamo_table):
    ag = _agendar(nome="João", telefone="9999").json()
    pid = _aluno("João Silva")
    resp = client.put(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", json={"pacienteId": pid})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pacienteId"] == pid
    assert body["nome"] == "João Silva"
    assert body["novo"] is False
    assert _listar().json()[0]["novo"] is False


def test_vincular_ja_vinculado_retorna_404(dynamo_table):
    pid = _aluno()
    ag = _agendar(pacienteId=pid).json()
    resp = client.put(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", json={"pacienteId": _aluno("B")})
    assert resp.status_code == 404


def test_vincular_paciente_inexistente_retorna_404(dynamo_table):
    ag = _agendar(nome="João").json()
    resp = client.put(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", json={"pacienteId": "nao-existe"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Aluno não encontrado"


# --- Desmarcar ---


def test_desmarcar(dynamo_table):
    ag = _agendar(nome="Ana").json()
    resp = client.delete(f"/agenda/{ag['data']}/07%3A00/{ag['id']}")
    assert resp.status_code == 200
    assert _listar().json() == []


def test_desmarcar_inexistente_retorna_404(dynamo_table):
    assert client.delete("/agenda/2026-10-19/07%3A00/nao-existe").status_code == 404


def test_desmarcar_de_outra_clinica_retorna_404(dynamo_table):
    ag = _agendar(nome="Ana").json()
    resp = client.delete(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", headers=OUTRA)
    assert resp.status_code == 404
    assert len(_listar().json()) == 1


def test_desmarcar_hora_invalida_retorna_400(dynamo_table):
    assert client.delete("/agenda/2026-10-19/7h/abc").status_code == 400
