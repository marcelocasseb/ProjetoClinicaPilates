"""Modelos Pydantic de Aparelho (feature cadastro-aparelhos, APR-03/09).

- `nome` é o único obrigatório; só-espaços é tratado como vazio e rejeitado.
- `categoria` (texto livre) e `descricao` são opcionais; vazios viram `None`.
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class AparelhoBase(BaseModel):
    """Campos comuns de criação/edição do aparelho."""

    model_config = ConfigDict(extra="ignore")

    nome: str
    categoria: Optional[str] = None
    descricao: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _exige_nome(cls, data):
        """`nome` obrigatório: ausente, nulo, vazio ou só-espaços → msg clara."""
        if isinstance(data, dict):
            nome = data.get("nome")
            if not isinstance(nome, str) or not nome.strip():
                raise ValueError("nome é obrigatório")
        return data

    @field_validator("nome")
    @classmethod
    def _trim_nome(cls, v):
        return v.strip()

    @field_validator("categoria", "descricao", mode="before")
    @classmethod
    def _vazio_para_none(cls, v):
        if not isinstance(v, str):
            return v
        v = v.strip()
        return v or None


class AparelhoCreate(AparelhoBase):
    """Payload de criação (`POST /aparelhos`)."""


class AparelhoUpdate(AparelhoBase):
    """Payload de edição (`PUT /aparelhos/{id}`) — `nome` segue obrigatório."""


class AparelhoOut(BaseModel):
    """Representação de saída do aparelho."""

    model_config = ConfigDict(extra="ignore")

    id: str
    nome: str
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    ativo: bool = True
    criadoEm: str
    atualizadoEm: str
