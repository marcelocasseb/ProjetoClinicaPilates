"""Modelos Pydantic de Tipo de treino (os botões de treino da aula do Pilates).

- `nome` é o único campo e é obrigatório; só-espaços é tratado como vazio e rejeitado.
- Espaços repetidos são juntados e a primeira letra vai para maiúscula
  ("  membros   superiores" → "Membros superiores").
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app import normaliza

NOME_MAX = 60


class TipoTreinoBase(BaseModel):
    """Payload de criação/edição do tipo de treino."""

    model_config = ConfigDict(extra="ignore")

    nome: str

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
        v = normaliza.espacos(v)
        v = v[:1].upper() + v[1:]
        if len(v) > NOME_MAX:
            raise ValueError(f"nome deve ter no máximo {NOME_MAX} caracteres")
        return v


class TipoTreinoOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    nome: str
    ativo: bool = True
    criadoEm: str
    atualizadoEm: str
