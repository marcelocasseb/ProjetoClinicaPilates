"""Smoke test do handler Mangum (INFRA-03).

Invoca o handler com um evento mínimo de API Gateway HTTP API (payload v2.0)
para /health e valida que a adaptação Lambda -> FastAPI responde 200.
"""
from app.handler import handler


def _api_gateway_v2_event(method: str, path: str) -> dict:
    return {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"host": "test.local", "content-length": "0"},
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
            },
            "requestId": "test-request-id",
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }


def test_handler_responde_200_no_health():
    event = _api_gateway_v2_event("GET", "/health")
    response = handler(event, None)
    assert response["statusCode"] == 200
    assert "ok" in response["body"]
