"""Aplicação FastAPI da clínica de Pilates.

Uma única app com roteamento interno, exposta ao Lambda via Mangum (ver handler.py).
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import pacientes

app = FastAPI(title="Clínica de Pilates API")

app.include_router(pacientes.router)


@app.exception_handler(RequestValidationError)
async def erro_de_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Converte erros de validação de entrada em 400 com mensagem legível.

    A spec de pacientes pede 400 (não o 422 padrão do FastAPI). Pega a primeira
    mensagem e remove o prefixo técnico "Value error, " do Pydantic.
    """
    erros = exc.errors()
    msg = erros[0].get("msg", "Requisição inválida") if erros else "Requisição inválida"
    msg = msg.removeprefix("Value error, ")
    return JSONResponse(status_code=400, content={"detail": msg})


@app.get("/health")
def health() -> dict[str, str]:
    """Health check — confirma que o serviço está no ar."""
    return {"status": "ok"}
