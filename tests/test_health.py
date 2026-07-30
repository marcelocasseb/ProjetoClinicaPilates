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


# Preflight CORS não é mais responsabilidade do app (M3/AUTH-03): passou para o
# API Gateway (CorsConfiguration no template.yaml), porque com o JWT Authorizer na
# borda o OPTIONS não pode chegar à Lambda. O comportamento do preflight é validado
# no deploy real (T7), não em teste unitário do FastAPI.
