"""Modelos Pydantic de Profissional (quem atende na Agenda).

- `nome` é o único obrigatório; só-espaços é tratado como vazio e rejeitado.
- `telefone` é opcional; vazio vira `None`.
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app import normaliza

NOME_MAX = 120
TELEFONE_MAX = 30


class ProfissionalBase(BaseModel):
    """Campos de criação/edição do profissional."""

    model_config = ConfigDict(extra="ignore")

    nome: str
    telefone: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _exige_nome(cls, data):
        if isinstance(data, dict):
            nome = data.get("nome")
            if not isinstance(nome, str) or not nome.strip():
                raise ValueError("nome é obrigatório")
        return data

    @field_validator("nome")
    @classmethod
    def _valida_nome(cls, v):
        v = normaliza.nome_proprio(v)
        if len(v) > NOME_MAX:
            raise ValueError(f"nome deve ter no máximo {NOME_MAX} caracteres")
        return v

    @field_validator("telefone", mode="before")
    @classmethod
    def _valida_telefone(cls, v):
        if not isinstance(v, str):
            return v
        v = v.strip()
        if len(v) > TELEFONE_MAX:
            raise ValueError(f"telefone deve ter no máximo {TELEFONE_MAX} caracteres")
        return normaliza.telefone(v) or None


class ProfissionalOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    nome: str
    telefone: Optional[str] = None
    ativo: bool = True
    criadoEm: str
    atualizadoEm: str
