"""Endpoints de CRUD de sessões/aulas de um paciente (feature registro-sessoes).

Rotas aninhadas no paciente (`/pacientes/{paciente_id}/sessoes`), multi-tenant
(AD-007). O `clinicId` vem de `get_clinic_id` (deps.py). Uma dependência de router
exige que o paciente exista e esteja ativo na clínica do solicitante — isso cobre
SES-06 (404 para paciente inexistente) e o isolamento entre clínicas.

Aula sem aparelho é barrada na validação do schema (SES-06/10) e vira 400 legível
via handler global de `RequestValidationError` (main.py).
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_clinic_id
from app.repository import PacienteRepository
from app.repository_sessao import SessaoRepository
from app.schemas_sessao import SessaoCreate, SessaoOut, SessaoUpdate


def exigir_paciente(paciente_id: str, clinic_id: str = Depends(get_clinic_id)) -> None:
    """Barra a requisição com 404 se o paciente não existe/está removido na clínica."""
    if PacienteRepository(clinic_id=clinic_id).get(paciente_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")


router = APIRouter(
    prefix="/pacientes/{paciente_id}/sessoes",
    tags=["sessoes"],
    dependencies=[Depends(exigir_paciente)],
)


def get_repository(
    paciente_id: str, clinic_id: str = Depends(get_clinic_id)
) -> SessaoRepository:
    return SessaoRepository(clinic_id=clinic_id, paciente_id=paciente_id)


@router.post("", response_model=SessaoOut, status_code=status.HTTP_201_CREATED)
def criar_sessao(
    payload: SessaoCreate,
    repo: SessaoRepository = Depends(get_repository),
) -> dict:
    """Registra uma aula do paciente (SES-01). `data` default hoje."""
    return repo.create(payload.model_dump())


@router.get("", response_model=list[SessaoOut])
def listar_sessoes(
    repo: SessaoRepository = Depends(get_repository),
) -> list[dict]:
    """Lista as aulas ativas do paciente (SES-04), mais recente primeiro."""
    return repo.list_ativos()


@router.get("/{sessao_id}", response_model=SessaoOut)
def obter_sessao(
    sessao_id: str,
    repo: SessaoRepository = Depends(get_repository),
) -> dict:
    """Retorna uma aula ativa do paciente (SES-05); `404` se não existe/removida/de outra clínica."""
    sessao = repo.get(sessao_id)
    if sessao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada"
        )
    return sessao


@router.put("/{sessao_id}", response_model=SessaoOut)
def editar_sessao(
    sessao_id: str,
    payload: SessaoUpdate,
    repo: SessaoRepository = Depends(get_repository),
) -> dict:
    """Atualiza uma aula do paciente (SES-07); `404` se não existe/removida/de outra clínica."""
    atualizado = repo.update(sessao_id, payload.model_dump())
    if atualizado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada"
        )
    return atualizado


@router.delete("/{sessao_id}")
def remover_sessao(
    sessao_id: str,
    repo: SessaoRepository = Depends(get_repository),
) -> dict:
    """Remove logicamente a aula (SES-08, soft delete).

    Retorna `200` com mensagem de sucesso; `404` se não existe/já removida/de outra clínica.
    """
    if not repo.soft_delete(sessao_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada"
        )
    return {"detail": "Aula removida com sucesso"}
