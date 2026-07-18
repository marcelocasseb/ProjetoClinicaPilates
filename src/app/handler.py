"""Entrypoint da AWS Lambda.

O Mangum adapta o app ASGI (FastAPI) para o formato de evento/resposta do Lambda
via API Gateway. Este `handler` é o alvo referenciado no template SAM
(`Handler: app.handler.handler`).
"""
from mangum import Mangum

from app.main import app

handler = Mangum(app)
