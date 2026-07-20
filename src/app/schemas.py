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

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def _exige_nome(cls, data):
        """`nome` é obrigatório: ausente, nulo, vazio ou só-espaços → rejeita com msg clara.

        Roda antes da validação de tipo, então captura todos os casos (inclusive
        campo ausente) com uma única mensagem em vez do erro técnico do Pydantic.
        """
        if isinstance(data, dict):
            nome = data.get("nome")
            if not isinstance(nome, str) or not nome.strip():
                raise ValueError("nome é obrigatório")
        return data

    @field_validator("nome")
    @classmethod
    def _trim_nome(cls, v):
        return v.strip()

    @field_validator("dataNascimento", "endereco", "telefone", "email", mode="before")
    @classmethod
    def _vazio_para_none(cls, v):
        """Opcionais: strings viram trimmed; vazio/só-espaços vira None."""
        if not isinstance(v, str):
            return v
        v = v.strip()
        return v or None

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
