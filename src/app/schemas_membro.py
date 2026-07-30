"""Modelos Pydantic de Membro da equipe (AUTH-07).

O admin informa só o `email`. `clinicId` e `role` NUNCA vêm do corpo (AD-012): a
clínica é herdada do token do admin e o papel é sempre `membro` — campos extras
(inclusive tentativas de mandar clinicId/role) são ignorados.
"""
from pydantic import BaseModel, ConfigDict, field_validator


class MembroCreate(BaseModel):
    """Payload de criação de membro (`POST /membros`). Só `email` é aceito."""

    model_config = ConfigDict(extra="ignore")

    email: str

    @field_validator("email", mode="before")
    @classmethod
    def _exige_email(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("email é obrigatório")
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("email inválido")
        return v


class MembroOut(BaseModel):
    """Resposta: e-mail criado + senha temporária (mostrada ao admin, D2)."""

    email: str
    senha_temporaria: str
