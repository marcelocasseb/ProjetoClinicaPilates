"""Testes do endpoint de health (INFRA-02)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_retorna_200_e_status_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rota_inexistente_retorna_404():
    response = client.get("/rota-que-nao-existe")
    assert response.status_code == 404
