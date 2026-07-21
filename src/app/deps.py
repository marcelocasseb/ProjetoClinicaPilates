"""Dependências compartilhadas entre os routers.

`get_clinic_id` resolve a clínica do solicitante (multi-tenant, AD-007). Enquanto o
login (Cognito, M3) não existe, vem de um header opcional `X-Clinic-Id` (útil para
testes e multi-clínica local) ou cai no default. Quando o login existir, SÓ esta
função muda — passa a extrair o `clinicId` do token; os routers continuam iguais.
"""
from typing import Optional

from fastapi import Header

DEFAULT_CLINIC_ID = "default"


def get_clinic_id(x_clinic_id: Optional[str] = Header(default=None)) -> str:
    return x_clinic_id or DEFAULT_CLINIC_ID
