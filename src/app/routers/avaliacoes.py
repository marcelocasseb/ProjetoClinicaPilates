"""Endpoints de CRUD de avaliações de um paciente (feature avaliacao-pacientes).

Rotas aninhadas no paciente (`/pacientes/{paciente_id}/avaliacoes`), multi-tenant
(AD-007). O `clinicId` vem de `get_clinic_id` (deps.py). Uma dependência de router
exige que o paciente exista e esteja ativo na clínica do solicitante — isso cobre
AVL-04 (404 para paciente inexistente) e o isolamento entre clínicas.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_clinic_id
from app.repository import PacienteRepository
from app.repository_avaliacao import AvaliacaoRepository
from app.schemas_avaliacao import AvaliacaoCreate, AvaliacaoOut, AvaliacaoUpdate


def exigir_paciente(paciente_id: str, clinic_id: str = Depends(get_clinic_id)) -> None:
    """Barra a requisição com 404 se o paciente não existe/está removido na clínica."""
    if PacienteRepository(clinic_id=clinic_id).get(paciente_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")


router = APIRouter(
    prefix="/pacientes/{paciente_id}/avaliacoes",
    tags=["avaliacoes"],
    dependencies=[Depends(exigir_paciente)],
)


def get_repository(
    paciente_id: str, clinic_id: str = Depends(get_clinic_id)
) -> AvaliacaoRepository:
    return AvaliacaoRepository(clinic_id=clinic_id, paciente_id=paciente_id)


@router.post("", response_model=AvaliacaoOut, status_code=status.HTTP_201_CREATED)
def criar_avaliacao(
    payload: AvaliacaoCreate,
    repo: AvaliacaoRepository = Depends(get_repository),
) -> dict:
    """Registra uma avaliação do paciente (AVL-01). `data` default hoje."""
    return repo.create(payload.model_dump())


@router.get("", response_model=list[AvaliacaoOut])
def listar_avaliacoes(
    repo: AvaliacaoRepository = Depends(get_repository),
) -> list[dict]:
    """Lista as avaliações ativas do paciente (AVL-05), mais recente primeiro."""
    return repo.list_ativos()


@router.get("/{avaliacao_id}", response_model=AvaliacaoOut)
def obter_avaliacao(
    avaliacao_id: str,
    repo: AvaliacaoRepository = Depends(get_repository),
) -> dict:
    """Retorna uma avaliação ativa do paciente (AVL-06); `404` se não existe/removida/de outra clínica."""
    avaliacao = repo.get(avaliacao_id)
    if avaliacao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada"
        )
    return avaliacao


@router.put("/{avaliacao_id}", response_model=AvaliacaoOut)
def editar_avaliacao(
    avaliacao_id: str,
    payload: AvaliacaoUpdate,
    repo: AvaliacaoRepository = Depends(get_repository),
) -> dict:
    """Atualiza uma avaliação do paciente (AVL-07); `404` se não existe/removida/de outra clínica."""
    atualizado = repo.update(avaliacao_id, payload.model_dump())
    if atualizado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada"
        )
    return atualizado


@router.delete("/{avaliacao_id}")
def remover_avaliacao(
    avaliacao_id: str,
    repo: AvaliacaoRepository = Depends(get_repository),
) -> dict:
    """Remove logicamente a avaliação (AVL-08, soft delete).

    Retorna `200` com mensagem de sucesso; `404` se não existe/já removida/de outra clínica.
    """
    if not repo.soft_delete(avaliacao_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada"
        )
    return {"detail": "Avaliação removida com sucesso"}
