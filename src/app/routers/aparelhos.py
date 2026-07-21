"""Endpoints de CRUD de aparelhos (feature cadastro-aparelhos).

Catálogo de aparelhos por clínica (multi-tenant, AD-007). O repositório é injetado
via `Depends` e escopado por clínica pelo `clinicId` de `get_clinic_id` (deps.py).
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_clinic_id
from app.repository_aparelho import AparelhoRepository
from app.schemas_aparelho import AparelhoCreate, AparelhoOut, AparelhoUpdate

router = APIRouter(prefix="/aparelhos", tags=["aparelhos"])


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> AparelhoRepository:
    return AparelhoRepository(clinic_id=clinic_id)


@router.post("", response_model=AparelhoOut, status_code=status.HTTP_201_CREATED)
def criar_aparelho(
    payload: AparelhoCreate,
    repo: AparelhoRepository = Depends(get_repository),
) -> dict:
    """Cadastra um aparelho na clínica (APR-01). Só `nome` é obrigatório."""
    return repo.create(payload.model_dump())


@router.get("", response_model=list[AparelhoOut])
def listar_aparelhos(
    repo: AparelhoRepository = Depends(get_repository),
) -> list[dict]:
    """Lista os aparelhos ativos da clínica (APR-04); removidos são omitidos."""
    return repo.list_ativos()


@router.get("/{aparelho_id}", response_model=AparelhoOut)
def obter_aparelho(
    aparelho_id: str,
    repo: AparelhoRepository = Depends(get_repository),
) -> dict:
    """Retorna um aparelho ativo da clínica (APR-05); `404` se não existe/removido/de outra clínica."""
    aparelho = repo.get(aparelho_id)
    if aparelho is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aparelho não encontrado")
    return aparelho


@router.put("/{aparelho_id}", response_model=AparelhoOut)
def editar_aparelho(
    aparelho_id: str,
    payload: AparelhoUpdate,
    repo: AparelhoRepository = Depends(get_repository),
) -> dict:
    """Atualiza um aparelho da clínica (APR-06); `404` se não existe/removido/de outra clínica."""
    atualizado = repo.update(aparelho_id, payload.model_dump())
    if atualizado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aparelho não encontrado")
    return atualizado


@router.delete("/{aparelho_id}")
def remover_aparelho(
    aparelho_id: str,
    repo: AparelhoRepository = Depends(get_repository),
) -> dict:
    """Remove logicamente o aparelho (APR-07, soft delete).

    Retorna `200` com mensagem de sucesso; `404` se não existe/já removido/de outra clínica.
    """
    if not repo.soft_delete(aparelho_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aparelho não encontrado")
    return {"detail": "Aparelho removido com sucesso"}
