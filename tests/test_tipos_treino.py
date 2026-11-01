"""Testes do cadastro de Tipos de treino (Parametrização → Tipos de treino)."""
from fastapi.testclient import TestClient

from app.main import app
from app.repository_tipo_treino import TIPOS_PADRAO

client = TestClient(app)

OUTRA = {"X-Clinic-Id": "clinica-corpo"}


def _nomes(headers=None):
    return [t["nome"] for t in client.get("/tipos-treino", headers=headers or {}).json()]


def _id(nome):
    return next(t["id"] for t in client.get("/tipos-treino").json() if t["nome"] == nome)


# --- Lista padrão ---


def test_primeira_listagem_traz_os_tipos_padrao_em_ordem_alfabetica(dynamo_table):
    nomes = _nomes()
    assert sorted(nomes) == sorted(TIPOS_PADRAO)
    assert nomes[:2] == ["Abdômen", "Alongamento"]


def test_padrao_e_semeado_uma_vez_so(dynamo_table):
    _nomes()
    assert len(_nomes()) == len(TIPOS_PADRAO)


def test_remover_todos_nao_ressemeia(dynamo_table):
    for t in client.get("/tipos-treino").json():
        assert client.delete(f"/tipos-treino/{t['id']}").status_code == 200
    assert _nomes() == []


def test_cada_clinica_tem_a_sua_lista(dynamo_table):
    client.post("/tipos-treino", json={"nome": "Respiração"})
    assert "Respiração" in _nomes()
    assert "Respiração" not in _nomes(OUTRA)
    assert len(_nomes(OUTRA)) == len(TIPOS_PADRAO)


# --- Cadastro ---


def test_criar_padroniza_o_nome(dynamo_table):
    resp = client.post("/tipos-treino", json={"nome": "  equilíbrio   e  core "})
    assert resp.status_code == 201
    assert resp.json()["nome"] == "Equilíbrio e core"
    assert "Equilíbrio e core" in _nomes()


def test_nome_obrigatorio(dynamo_table):
    resp = client.post("/tipos-treino", json={"nome": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "nome é obrigatório"


def test_nome_duplicado_ignora_maiusculas_e_acentos(dynamo_table):
    resp = client.post("/tipos-treino", json={"nome": "ABDOMEN"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Já existe um tipo de treino com esse nome"


def test_editar_renomeia(dynamo_table):
    tid = _id("Força")
    resp = client.put(f"/tipos-treino/{tid}", json={"nome": "Fortalecimento"})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Fortalecimento"
    assert "Força" not in _nomes()


def test_editar_mantendo_o_proprio_nome_nao_e_duplicado(dynamo_table):
    tid = _id("Força")
    assert client.put(f"/tipos-treino/{tid}", json={"nome": "força"}).status_code == 200


def test_editar_para_nome_de_outro_e_duplicado(dynamo_table):
    tid = _id("Força")
    assert client.put(f"/tipos-treino/{tid}", json={"nome": "Postural"}).status_code == 409


def test_remover_some_da_lista_e_libera_o_nome(dynamo_table):
    tid = _id("Postural")
    assert client.delete(f"/tipos-treino/{tid}").status_code == 200
    assert "Postural" not in _nomes()
    assert client.delete(f"/tipos-treino/{tid}").status_code == 404
    assert client.put(f"/tipos-treino/{tid}", json={"nome": "X"}).status_code == 404
    assert client.post("/tipos-treino", json={"nome": "Postural"}).status_code == 201


def test_outra_clinica_nao_mexe_no_tipo(dynamo_table):
    tid = _id("Postural")
    assert client.delete(f"/tipos-treino/{tid}", headers=OUTRA).status_code == 404
    assert client.put(f"/tipos-treino/{tid}", json={"nome": "X"}, headers=OUTRA).status_code == 404
    assert "Postural" in _nomes()


def test_aula_antiga_mantem_o_treino_renomeado(dynamo_table):
    """A aula guarda o texto: renomear o tipo não reescreve o histórico."""
    pid = client.post("/pacientes", json={"nome": "Ana"}).json()["id"]
    aid = client.post("/aparelhos", json={"nome": "Chair"}).json()["id"]
    sessao = {
        "data": "2026-10-30",
        "aparelhos": [{"aparelhoId": aid, "nome": "Chair", "treinos": ["Força"]}],
    }
    assert client.post(f"/pacientes/{pid}/sessoes", json=sessao).status_code == 201
    client.put(f"/tipos-treino/{_id('Força')}", json={"nome": "Fortalecimento"})
    aula = client.get(f"/pacientes/{pid}/sessoes").json()[0]
    assert aula["aparelhos"][0]["treinos"] == ["Força"]
