"""Modelos Pydantic de Paciente (validação de entrada/saída).

Regras:
- `nome` é o único campo obrigatório; só-espaços é tratado como vazio e rejeitado.
- `cpf` é opcional, mas validado (11 dígitos + dígitos verificadores) quando informado;
  armazenado normalizado (só números). Ver AD-008.
- `endereco` é um objeto aninhado (MAP) opcional, preenchido via CEP no front (ViaCEP);
  o back apenas valida e armazena. Ver AD-009.
- `email` é validado por regex simples (evita a dependência `email-validator`).
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


def _cpf_valido(digits: str) -> bool:
    """Valida um CPF (só dígitos) pelos dois dígitos verificadores."""
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(digits[num]) * ((i + 1) - num) for num in range(i))
        dig = (soma * 10) % 11
        if dig == 10:
            dig = 0
        if dig != int(digits[i]):
            return False
    return True


class Endereco(BaseModel):
    """Endereço do paciente (MAP). Campos preenchidos pelo CEP no front (AD-009)."""

    model_config = ConfigDict(extra="ignore")

    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None

    @field_validator("*", mode="before")
    @classmethod
    def _vazio_para_none(cls, v):
        if not isinstance(v, str):
            return v
        v = v.strip()
        return v or None

    @field_validator("cep")
    @classmethod
    def _valida_cep(cls, v):
        if v is None:
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) != 8:
            raise ValueError("cep deve ter 8 dígitos")
        return digits

    @field_validator("uf")
    @classmethod
    def _valida_uf(cls, v):
        if v is None:
            return None
        v = v.upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("uf deve ter 2 letras")
        return v


class PacienteBase(BaseModel):
    """Campos comuns de criação/edição, com as validações da spec."""

    model_config = ConfigDict(extra="ignore")

    nome: str
    cpf: Optional[str] = None
    dataNascimento: Optional[str] = None
    endereco: Optional[Endereco] = None
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

    @field_validator("endereco", mode="before")
    @classmethod
    def _endereco_vazio_para_none(cls, v):
        """Endereço vazio ("" ou {}) vira None em vez de virar erro de tipo."""
        if v is None or v == {}:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("cpf", "dataNascimento", "telefone", "email", mode="before")
    @classmethod
    def _vazio_para_none(cls, v):
        """Opcionais string: trimmed; vazio/só-espaços vira None."""
        if not isinstance(v, str):
            return v
        v = v.strip()
        return v or None

    @field_validator("cpf")
    @classmethod
    def _valida_cpf(cls, v):
        if v is None:
            return None
        digits = re.sub(r"\D", "", v)
        if not _cpf_valido(digits):
            raise ValueError("CPF inválido")
        return digits

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
    cpf: Optional[str] = None
    dataNascimento: Optional[str] = None
    endereco: Optional[Endereco] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativo: bool = True
    criadoEm: str
    atualizadoEm: str
