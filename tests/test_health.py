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


def test_preflight_cors_responde_ok():
    # Preflight do navegador (OPTIONS com Origin + método pedido) deve passar,
    # senão o front toma "Failed to fetch". CORS é tratado pelo CORSMiddleware.
    response = client.options(
        "/pacientes",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-clinic-id,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
