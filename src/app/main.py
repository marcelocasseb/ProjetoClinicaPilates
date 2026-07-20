"""Aplicação FastAPI da clínica de Pilates.

Uma única app com roteamento interno, exposta ao Lambda via Mangum (ver handler.py).
"""
from fastapi import FastAPI

from app.routers import pacientes

app = FastAPI(title="Clínica de Pilates API")

app.include_router(pacientes.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check — confirma que o serviço está no ar."""
    return {"status": "ok"}
