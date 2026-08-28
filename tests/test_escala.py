"""Testes dos endpoints da Escala Semanal (ESC-01, 03..09)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OUTRA = {"X-Clinic-Id": "clinica-corpo"}


def _aluno(nome="Rebecca", headers=None):
    """Cria um paciente e devolve o id (a matrícula sempre pende de um aluno real)."""
    return client.post("/pacientes", json={"nome": nome}, headers=headers or {}).json()["id"]


def _matricular(paciente_id, dia=1, hora="07:00", headers=None):
    return client.post(
        "/escala",
        json={"dia": dia, "hora": hora, "pacienteId": paciente_id},
        headers=headers or {},
    )


# --- Matricular (ESC-03, ESC-04, ESC-06) ---


def test_matricular_retorna_201(dynamo_table):
    resp = _matricular(_aluno())
    assert resp.status_code == 201
    body = resp.json()
    assert body["dia"] == 1
    assert body["hora"] == "07:00"
    assert body["nome"] == "Rebecca"
    assert body["criadoEm"]


def test_matricular_aparece_na_grade(dynamo_table):
    _matricular(_aluno())
    grade = client.get("/escala").json()
    assert len(grade) == 1
    assert grade[0]["nome"] == "Rebecca"


def test_matricular_duplicado_retorna_409(dynamo_table):
    pid = _aluno()
    assert _matricular(pid).status_code == 201
    resp = _matricular(pid)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Este aluno já está neste horário"
    assert len(client.get("/escala").json()) == 1


def test_mesmo_aluno_em_dias_diferentes(dynamo_table):
    """Caso normal da clínica: seg e qua às 7h."""
    pid = _aluno()
    assert _matricular(pid, dia=1).status_code == 201
    assert _matricular(pid, dia=3).status_code == 201
    assert len(client.get("/escala").json()) == 2


def test_matricular_aluno_inexistente_retorna_404(dynamo_table):
    resp = _matricular("nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Aluno não encontrado"


def test_matricular_aluno_removido_retorna_404(dynamo_table):
    pid = _aluno()
    client.delete(f"/pacientes/{pid}")
    assert _matricular(pid).status_code == 404


# --- Validação (ESC-07) ---


def test_dia_fora_do_intervalo_retorna_400(dynamo_table):
    resp = _matricular(_aluno(), dia=8)
    assert resp.status_code == 400
    assert "dia" in resp.json()["detail"]


def test_hora_sem_zero_a_esquerda_retorna_400(dynamo_table):
    resp = _matricular(_aluno(), hora="7:00")
    assert resp.status_code == 400
    assert "hora" in resp.json()["detail"]


def test_hora_invalida_retorna_400(dynamo_table):
    assert _matricular(_aluno(), hora="25:00").status_code == 400


def test_paciente_id_vazio_retorna_400(dynamo_table):
    assert _matricular("", ).status_code == 400


def test_delete_com_dia_invalido_retorna_400(dynamo_table):
    resp = client.delete("/escala/9/07:00/p1")
    assert resp.status_code == 400
    assert "dia" in resp.json()["detail"]


def test_delete_com_hora_invalida_retorna_400(dynamo_table):
    resp = client.delete("/escala/1/7h/p1")
    assert resp.status_code == 400
    assert "hora" in resp.json()["detail"]


# --- Grade (ESC-01) ---


def test_grade_vazia(dynamo_table):
    assert client.get("/escala").json() == []


def test_grade_ordenada_por_dia_hora_nome(dynamo_table):
    ana = _aluno("Ana")
    zeca = _aluno("Zeca")
    _matricular(zeca, dia=1, hora="07:00")
    _matricular(ana, dia=1, hora="07:00")
    _matricular(ana, dia=1, hora="19:00")
    _matricular(ana, dia=3, hora="07:00")
    grade = client.get("/escala").json()
    assert [(m["dia"], m["hora"], m["nome"]) for m in grade] == [
        (1, "07:00", "Ana"),
        (1, "07:00", "Zeca"),
        (1, "19:00", "Ana"),
        (3, "07:00", "Ana"),
    ]


def test_grade_nao_traz_aparelhos_da_mesma_particao(dynamo_table):
    """`APARELHO#` mora na mesma PK da clínica — não pode vazar na grade."""
    client.post("/aparelhos", json={"nome": "Reformer"})
    _matricular(_aluno())
    assert len(client.get("/escala").json()) == 1


# --- Desmatricular (ESC-05) ---


def test_remover_retorna_200_e_some_da_grade(dynamo_table):
    pid = _aluno()
    _matricular(pid)
    resp = client.delete(f"/escala/1/07:00/{pid}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Aluno removido do horário"
    assert client.get("/escala").json() == []


def test_remover_com_hora_percent_encoded(dynamo_table):
    """O front manda `07%3A00` (`encodeURIComponent`) — precisa cair na mesma rota."""
    pid = _aluno()
    _matricular(pid)
    assert client.delete(f"/escala/1/07%3A00/{pid}").status_code == 200
    assert client.get("/escala").json() == []


def test_remover_inexistente_retorna_404(dynamo_table):
    resp = client.delete("/escala/1/07:00/fantasma")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Matrícula não encontrada"


def test_remover_duas_vezes_retorna_404(dynamo_table):
    pid = _aluno()
    _matricular(pid)
    assert client.delete(f"/escala/1/07:00/{pid}").status_code == 200
    assert client.delete(f"/escala/1/07:00/{pid}").status_code == 404


def test_recolocar_no_mesmo_horario_depois_de_remover(dynamo_table):
    pid = _aluno()
    _matricular(pid)
    client.delete(f"/escala/1/07:00/{pid}")
    assert _matricular(pid).status_code == 201


# --- Coerência com o cadastro (ESC-09) ---


def test_aluno_removido_do_cadastro_some_da_grade(dynamo_table):
    pid = _aluno()
    _matricular(pid)
    client.delete(f"/pacientes/{pid}")
    assert client.get("/escala").json() == []


def test_aluno_renomeado_aparece_com_o_nome_novo(dynamo_table):
    pid = _aluno("Rebeca")
    _matricular(pid)
    client.put(f"/pacientes/{pid}", json={"nome": "Rebecca Machado"})
    assert client.get("/escala").json()[0]["nome"] == "Rebecca Machado"


# --- Isolamento multi-tenant (ESC-08) ---


def test_grade_de_outra_clinica_nao_aparece(dynamo_table):
    _matricular(_aluno())
    assert client.get("/escala", headers=OUTRA).json() == []


def test_outra_clinica_nao_remove_matricula(dynamo_table):
    pid = _aluno()
    _matricular(pid)
    assert client.delete(f"/escala/1/07:00/{pid}", headers=OUTRA).status_code == 404
    assert len(client.get("/escala").json()) == 1


def test_nao_matricula_aluno_de_outra_clinica(dynamo_table):
    pid = _aluno()
    assert _matricular(pid, headers=OUTRA).status_code == 404


# --- Sem regressão ---


def test_rotas_existentes_seguem_de_pe(dynamo_table):
    assert client.get("/health").status_code == 200
    assert client.get("/pacientes").status_code == 200
    assert client.get("/aparelhos").status_code == 200
