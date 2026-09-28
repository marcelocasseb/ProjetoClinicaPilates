"""Endpoint de provisionamento de membros da equipe (AUTH-07, AUTH-08).

Só **admin** pode adicionar membro (`require_admin`). O novo usuário herda o
`clinicId` do **token do admin** (nunca do corpo — AD-012) e nasce com
`role=membro`. A senha temporária é devolvida para o admin repassar (D2).

O nome vai para o Cognito (atributo `name`, chega no token) e o membro é registrado
no DynamoDB (`CLINIC#<id>` / `MEMBRO#<email>`). A ordem é Cognito → DynamoDB: se o
e-mail já existe, o 409 sai antes de qualquer gravação no banco.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, status

from app import cognito_admin
from app.deps import get_clinic_id, require_admin
from app.repository_clinica import ClinicaRepository
from app.schemas_membro import MembroCreate, MembroOut

router = APIRouter(prefix="/membros", tags=["membros"])


@router.post(
    "",
    response_model=MembroOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],  # AUTH-08: barra não-admin (403) antes de tudo
)
def adicionar_membro(
    payload: MembroCreate,
    clinic_id: str = Depends(get_clinic_id),
) -> dict:
    """Cria um membro na clínica do admin (herda clinicId do token; role=membro)."""
    user_pool_id = os.environ["USER_POOL_ID"]
    try:
        criado = cognito_admin.criar_usuario(
            payload.email,
            clinic_id,
            cognito_admin.ROLE_MEMBRO,
            nome=payload.nome,
            user_pool_id=user_pool_id,
        )
    except cognito_admin.EmailJaExiste as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    ClinicaRepository().set_membro(
        clinic_id, payload.email, payload.nome, cognito_admin.ROLE_MEMBRO
    )
    return criado
