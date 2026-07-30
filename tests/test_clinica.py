"""Testes do endpoint GET /clinica (nome de exibição da clínica)."""
from fastapi.testclient import TestClient

from app.main import app
from app.repository_clinica import ClinicaRepository

client = TestClient(app)


def test_clinica_sem_nome_retorna_none(dynamo_table):
    resp = client.get("/clinica", headers={"X-Clinic-Id": "clinica-a"})
    assert resp.status_code == 200
    assert resp.json() == {"clinicId": "clinica-a", "nome": None}


def test_clinica_com_nome(dynamo_table):
    ClinicaRepository(table_name=dynamo_table).set_nome("clinica-a", "Studio Corpo")
    resp = client.get("/clinica", headers={"X-Clinic-Id": "clinica-a"})
    assert resp.json() == {"clinicId": "clinica-a", "nome": "Studio Corpo"}


def test_nome_e_isolado_por_clinica(dynamo_table):
    ClinicaRepository(table_name=dynamo_table).set_nome("clinica-a", "Studio A")
    resp = client.get("/clinica", headers={"X-Clinic-Id": "clinica-b"})
    assert resp.json() == {"clinicId": "clinica-b", "nome": None}
