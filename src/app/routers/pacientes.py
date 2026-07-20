"""Endpoints de CRUD de pacientes (feature cadastro-pacientes).

Usa os schemas de validação (`app.schemas`) e o repositório DynamoDB
(`app.repository`). O repositório é injetado via `Depends`, o que permite
substituí-lo/mocká-lo nos testes e resolve `TABLE_NAME` por requisição.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.repository import PacienteRepository
from app.schemas import PacienteCreate, PacienteOut, PacienteUpdate

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


def get_repository() -> PacienteRepository:
    return PacienteRepository()


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


@router.delete("/{paciente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_paciente(
    paciente_id: str,
    repo: PacienteRepository = Depends(get_repository),
) -> None:
    """Remove logicamente o paciente (PAC-08, soft delete); `404` se não existe/já removido."""
    if not repo.soft_delete(paciente_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")
