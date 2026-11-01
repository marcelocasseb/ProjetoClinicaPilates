"""Endpoints do cadastro de Tipos de treino (os botões de treino da aula do Pilates).

Rotas de **nível clínica** (`/tipos-treino`, como `/aparelhos`), multi-tenant (AD-007),
liberadas a qualquer papel. Substitui a lista fixa do front (AD-011): a aula continua
guardando o texto do treino, então as aulas antigas não mudam.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_clinic_id
from app.repository_tipo_treino import TipoTreinoRepository
from app.schemas_tipo_treino import TipoTreinoBase, TipoTreinoOut

router = APIRouter(prefix="/tipos-treino", tags=["tipos-treino"])

NAO_ENCONTRADO = "Tipo de treino não encontrado"
DUPLICADO = "Já existe um tipo de treino com esse nome"


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> TipoTreinoRepository:
    return TipoTreinoRepository(clinic_id=clinic_id)


@router.get("", response_model=list[TipoTreinoOut])
def listar(repo: TipoTreinoRepository = Depends(get_repository)) -> list[dict]:
    """Tipos ativos da clínica, em ordem alfabética."""
    return repo.list_ativos()


@router.post("", response_model=TipoTreinoOut, status_code=status.HTTP_201_CREATED)
def criar(payload: TipoTreinoBase, repo: TipoTreinoRepository = Depends(get_repository)) -> dict:
    if repo.nome_em_uso(payload.nome):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    return repo.create(payload.model_dump())


@router.put("/{tipo_id}", response_model=TipoTreinoOut)
def editar(
    tipo_id: str,
    payload: TipoTreinoBase,
    repo: TipoTreinoRepository = Depends(get_repository),
) -> dict:
    """Renomear não altera as aulas já registradas (elas guardam o texto da época)."""
    if repo.get(tipo_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NAO_ENCONTRADO)
    if repo.nome_em_uso(payload.nome, exceto_id=tipo_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    atualizado = repo.update(tipo_id, payload.model_dump())
    if atualizado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NAO_ENCONTRADO)
    return atualizado


@router.delete("/{tipo_id}")
def remover(tipo_id: str, repo: TipoTreinoRepository = Depends(get_repository)) -> dict:
    """Remoção lógica: sai dos botões da aula, mas as aulas antigas mantêm o texto."""
    if not repo.soft_delete(tipo_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NAO_ENCONTRADO)
    return {"detail": "Tipo de treino removido"}
