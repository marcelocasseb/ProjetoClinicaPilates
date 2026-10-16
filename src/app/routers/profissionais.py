"""Endpoints do cadastro de Profissionais (quem atende na Agenda).

Rotas de **nível clínica** (`/profissionais`, como `/aparelhos`), multi-tenant
(AD-007), liberadas a qualquer papel — quem monta a agenda é a recepção.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_clinic_id
from app.repository_profissional import ProfissionalRepository
from app.schemas_profissional import ProfissionalBase, ProfissionalOut

router = APIRouter(prefix="/profissionais", tags=["profissionais"])

NAO_ENCONTRADO = "Profissional não encontrado"


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> ProfissionalRepository:
    return ProfissionalRepository(clinic_id=clinic_id)


@router.get("", response_model=list[ProfissionalOut])
def listar(repo: ProfissionalRepository = Depends(get_repository)) -> list[dict]:
    """Profissionais ativos da clínica, em ordem alfabética."""
    return repo.list_ativos()


@router.post("", response_model=ProfissionalOut, status_code=status.HTTP_201_CREATED)
def criar(payload: ProfissionalBase, repo: ProfissionalRepository = Depends(get_repository)) -> dict:
    return repo.create(payload.model_dump())


@router.put("/{profissional_id}", response_model=ProfissionalOut)
def editar(
    profissional_id: str,
    payload: ProfissionalBase,
    repo: ProfissionalRepository = Depends(get_repository),
) -> dict:
    atualizado = repo.update(profissional_id, payload.model_dump())
    if atualizado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NAO_ENCONTRADO)
    return atualizado


@router.delete("/{profissional_id}")
def remover(profissional_id: str, repo: ProfissionalRepository = Depends(get_repository)) -> dict:
    """Remoção lógica: marcações antigas continuam mostrando o nome."""
    if not repo.soft_delete(profissional_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NAO_ENCONTRADO)
    return {"detail": "Profissional removido"}
