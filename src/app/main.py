"""Aplicação FastAPI da clínica de Pilates.

Uma única app com roteamento interno, exposta ao Lambda via Mangum (ver handler.py).
"""
from fastapi import FastAPI

app = FastAPI(title="Clínica de Pilates API")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check — confirma que o serviço está no ar."""
    return {"status": "ok"}
