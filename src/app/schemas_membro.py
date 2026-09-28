"""Modelos Pydantic de Membro da equipe (AUTH-07).

O admin informa `nome` e `email`. `clinicId` e `role` NUNCA vêm do corpo (AD-012): a
clínica é herdada do token do admin e o papel é sempre `membro` — campos extras
(inclusive tentativas de mandar clinicId/role) são ignorados.

O `nome` vai para o atributo `name` do Cognito (chega no token — saudação da tela
inicial, profissional pré-preenchido no Pilates) e para o registro do membro no
DynamoDB.
"""
from pydantic import BaseModel, ConfigDict, field_validator

NOME_MAX = 80


def valida_nome(v) -> str:
    """Nome da pessoa: obrigatório, espaços colapsados, até NOME_MAX caracteres.

    Compartilhado com o script de onboarding (`criar_clinica.py`), para o admin da
    clínica nova e o membro seguirem a mesma regra.
    """
    if not isinstance(v, str) or not v.strip():
        raise ValueError("nome é obrigatório")
    nome = " ".join(v.split())
    if len(nome) > NOME_MAX:
        raise ValueError(f"nome deve ter no máximo {NOME_MAX} caracteres")
    return nome


class MembroCreate(BaseModel):
    """Payload de criação de membro (`POST /membros`). Aceita só `nome` e `email`."""

    model_config = ConfigDict(extra="ignore")

    nome: str
    email: str

    @field_validator("nome", mode="before")
    @classmethod
    def _exige_nome(cls, v):
        return valida_nome(v)

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
    """Resposta: nome e e-mail criados + senha temporária (mostrada ao admin, D2)."""

    nome: str
    email: str
    senha_temporaria: str
