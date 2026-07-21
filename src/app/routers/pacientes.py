"""Endpoints de CRUD de pacientes (feature cadastro-pacientes).

Usa os schemas de validação (`app.schemas`) e o repositório DynamoDB
(`app.repository`). O repositório é injetado via `Depends` e é **escopado por
clínica** (multi-tenant, AD-007): o `clinicId` vem de `get_clinic_id`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.repository import PacienteRepository
from app.schemas import PacienteCreate, PacienteOut, PacienteUpdate

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

# Enquanto o login (Cognito, M3) não existe, o clinicId vem de um header opcional
# (`X-Clinic-Id`, útil para testes e multi-clínica local) ou cai no default.
# Quando o login existir, `get_clinic_id` passará a extrair o clinicId do token —
# e SÓ este ponto muda; o resto do código continua igual.
DEFAULT_CLINIC_ID = "default"


def get_clinic_id(x_clinic_id: Optional[str] = Header(default=None)) -> str:
    return x_clinic_id or DEFAULT_CLINIC_ID


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> PacienteRepository:
    return PacienteRepository(clinic_id=clinic_id)


@router.post("", response_model=PacienteOut, status_code=status.HTTP_201_CREATED)
def criar_paciente(
    payload: PacienteCreate,
    repo: PacienteRepository = Depends(get_repository),
) -> dict:
    """Cadastra um paciente (PAC-01). Só `nome` é obrigatório."""
    return repo.create(payload.model_dump())


@router.get("", response_model=list[PacienteOut])
def listar_pacientes(
    repo: PacienteRepository = Depends(get_repository),
) -> list[dict]:
    """Lista os pacientes ativos (PAC-05); removidos são omitidos."""
    return repo.list_ativos()


@router.get("/{paciente_id}", response_model=PacienteOut)
def obter_paciente(
    paciente_id: str,
    repo: PacienteRepository = Depends(get_repository),
) -> dict:
    """Retorna a ficha de um paciente ativo (PAC-06); `404` se não existe/removido."""
    paciente = repo.get(paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")
    return paciente


@router.put("/{paciente_id}", response_model=PacienteOut)
def editar_paciente(
    paciente_id: str,
    payload: PacienteUpdate,
    repo: PacienteRepository = Depends(get_repository),
) -> dict:
    """Atualiza o perfil de um paciente (PAC-07); `404` se não existe/removido."""
    atualizado = repo.update(paciente_id, payload.model_dump())
    if atualizado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")
    return atualizado


@router.delete("/{paciente_id}")
def remover_paciente(
    paciente_id: str,
    repo: PacienteRepository = Depends(get_repository),
) -> dict:
    """Remove logicamente o paciente (PAC-08, soft delete).

    Retorna `200` com mensagem de sucesso; `404` com "Paciente não encontrado"
    se o id não existe ou já foi removido.
    """
    if not repo.soft_delete(paciente_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")
    return {"detail": "Paciente removido com sucesso"}
