"""Modelos Pydantic de Paciente (validação de entrada/saída).

Regras (spec cadastro-pacientes, PAC-03/04/09):
- `nome` é o único campo obrigatório; só-espaços é tratado como vazio e rejeitado.
- `email` é validado por regex simples (evita a dependência `email-validator`,
  mantendo o ZIP da Lambda enxuto).
- `dataNascimento` deve ser `YYYY-MM-DD` e uma data de calendário válida.
- Campos opcionais enviados vazios ("" ou só-espaços) viram `None` (não persistem lixo).
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PacienteBase(BaseModel):
    """Campos comuns de criação/edição, com as validações da spec."""

    model_config = ConfigDict(extra="ignore")

    nome: str
    dataNascimento: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None

    @field_validator("nome", "dataNascimento", "endereco", "telefone", "email", mode="before")
    @classmethod
    def _strip_e_vazio_para_none(cls, v):
        """Normaliza: strings viram trimmed; vazio/só-espaços vira None."""
        if not isinstance(v, str):
            return v
        v = v.strip()
        return v or None

    @field_validator("nome")
    @classmethod
    def _nome_obrigatorio(cls, v):
        # Após a normalização acima, vazio/só-espaços chega como None.
        if not v:
            raise ValueError("nome é obrigatório")
        return v

    @field_validator("dataNascimento")
    @classmethod
    def _valida_data(cls, v):
        if v is None:
            return None
        if not _DATE_RE.match(v):
            raise ValueError("dataNascimento deve estar no formato YYYY-MM-DD")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("dataNascimento não é uma data válida")
        return v

    @field_validator("email")
    @classmethod
    def _valida_email(cls, v):
        if v is None:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("email inválido")
        return v


class PacienteCreate(PacienteBase):
    """Payload de criação (`POST /pacientes`)."""


class PacienteUpdate(PacienteBase):
    """Payload de edição (`PUT /pacientes/{id}`) — `nome` segue obrigatório (PAC-07)."""


class PacienteOut(BaseModel):
    """Representação de saída do paciente."""

    model_config = ConfigDict(extra="ignore")

    id: str
    nome: str
    dataNascimento: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativo: bool = True
    criadoEm: str
    atualizadoEm: str
