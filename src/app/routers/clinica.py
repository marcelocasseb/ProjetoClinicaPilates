"""Endpoint de dados da clínica do usuário logado (nome de exibição).

`GET /clinica` devolve `{clinicId, nome}` da clínica do solicitante — o `clinicId`
vem do token (get_clinic_id) e o `nome` dos metadados no DynamoDB (ou None se ainda
não gravado). O front usa isso para mostrar o nome da clínica no topo em vez do id.
"""
from fastapi import APIRouter, Depends

from app.deps import get_clinic_id
from app.repository_clinica import ClinicaRepository

router = APIRouter(prefix="/clinica", tags=["clinica"])


@router.get("")
def obter_clinica(clinic_id: str = Depends(get_clinic_id)) -> dict:
    """Dados da clínica do usuário logado (id + nome de exibição)."""
    nome = ClinicaRepository().get_nome(clinic_id)
    return {"clinicId": clinic_id, "nome": nome}
