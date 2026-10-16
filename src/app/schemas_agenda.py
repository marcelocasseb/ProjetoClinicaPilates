"""Modelos Pydantic da Agenda (feature agenda, AGD-01..08).

Um agendamento é uma marcação **datada**: "João vem na segunda, 19/10, às 7h". Ao
contrário da Escala (grade fixa que vale toda semana), vale só para aquela data — e não
tem nenhuma relação com a Escala.

Quem vem pode ser:
- um **paciente cadastrado** (`pacienteId`), cujo nome é resolvido ao vivo no router; ou
- uma **pessoa ainda sem cadastro** (`nome` + `telefone` opcional) — o caso típico é a
  aula experimental. Depois o agendamento pode ser **vinculado** a um paciente
  (`AgendaVincular`), quando a pessoa vira aluna.

Exatamente um dos dois: `pacienteId` **ou** `nome`.

- `data` é `YYYY-MM-DD` e precisa ser uma data de calendário válida.
- `hora` é `HH:MM` 24h com zero à esquerda (mesma regra da Escala: a hora entra no SK
  e só zerada a ordem alfabética coincide com a cronológica).
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
import re
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app import normaliza
from app.schemas_escala import _RE_HORA

_RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

NOME_MAX = 120
TELEFONE_MAX = 30


def valida_data(v) -> str:
    """`YYYY-MM-DD` de calendário válido (usado também nos query/path params)."""
    if not isinstance(v, str) or not _RE_DATA.match(v.strip()):
        raise ValueError("data deve estar no formato AAAA-MM-DD")
    v = v.strip()
    try:
        date.fromisoformat(v)
    except ValueError:
        raise ValueError("data inválida")
    return v


def valida_hora(v) -> str:
    if not isinstance(v, str) or not _RE_HORA.match(v.strip()):
        raise ValueError("hora deve estar no formato HH:MM (ex.: 07:00)")
    return v.strip()


def _texto_ou_none(v):
    """String trimmed; vazia/só-espaços vira None."""
    if not isinstance(v, str):
        return v
    v = v.strip()
    return v or None


class AgendaCreate(BaseModel):
    """Payload de `POST /agenda`."""

    model_config = ConfigDict(extra="ignore")

    data: str
    hora: str
    pacienteId: Optional[str] = None
    nome: Optional[str] = None
    telefone: Optional[str] = None
    profissionalId: Optional[str] = None  # opcional; conferido no router (404)

    @field_validator("data", mode="before")
    @classmethod
    def _valida_data(cls, v):
        return valida_data(v)

    @field_validator("hora", mode="before")
    @classmethod
    def _valida_hora(cls, v):
        return valida_hora(v)

    @field_validator("pacienteId", "nome", "telefone", "profissionalId", mode="before")
    @classmethod
    def _vazio_para_none(cls, v):
        return _texto_ou_none(v)

    @field_validator("nome")
    @classmethod
    def _padroniza_nome(cls, v):
        return normaliza.nome_proprio(v)

    @field_validator("telefone")
    @classmethod
    def _padroniza_telefone(cls, v):
        return normaliza.telefone(v)

    @model_validator(mode="after")
    def _paciente_ou_nome(self):
        if self.pacienteId and self.nome:
            raise ValueError("informe o paciente cadastrado ou o nome, não os dois")
        if not self.pacienteId and not self.nome:
            raise ValueError("informe o paciente ou o nome de quem vem")
        if self.nome and len(self.nome) > NOME_MAX:
            raise ValueError(f"nome deve ter no máximo {NOME_MAX} caracteres")
        if self.telefone and len(self.telefone) > TELEFONE_MAX:
            raise ValueError(f"telefone deve ter no máximo {TELEFONE_MAX} caracteres")
        if self.pacienteId:
            self.telefone = None  # o telefone de um cadastrado é o do cadastro
        return self


class AgendaVincular(BaseModel):
    """Payload de `PUT /agenda/{data}/{hora}/{id}`: liga a pessoa nova a um paciente."""

    model_config = ConfigDict(extra="ignore")

    pacienteId: str

    @field_validator("pacienteId", mode="before")
    @classmethod
    def _valida_paciente(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("pacienteId é obrigatório")
        return v.strip()


class AgendaProfissional(BaseModel):
    """Payload de `PUT /agenda/{data}/{hora}/{id}/profissional`. `null` tira o profissional."""

    model_config = ConfigDict(extra="ignore")

    profissionalId: Optional[str] = None

    @field_validator("profissionalId", mode="before")
    @classmethod
    def _vazio_para_none(cls, v):
        return _texto_ou_none(v)


class AgendaPagamento(BaseModel):
    """Payload de `POST /agenda/{data}/{hora}/{id}/pagamento` (botão "Receber").

    Vira uma **entrada** no Caixa. A Agenda não tem relação com o Pilates, então não há
    tipo de aula nem preço de tabela: o valor é digitado na hora. Valor e forma são
    revalidados pelas regras do próprio lançamento (`LancamentoCreate`) no router —
    centavos inteiros, nada de float. `dataPagamento` é o dia em que o dinheiro entrou
    (regime de caixa), mandado pelo front no fuso local; não é a data do agendamento.
    """

    model_config = ConfigDict(extra="ignore")

    valorCentavos: Any  # validado como no Caixa (float recusado) — ver docstring
    formaPagamento: Optional[str] = None
    dataPagamento: str

    @field_validator("dataPagamento", mode="before")
    @classmethod
    def _valida_data_pagamento(cls, v):
        return valida_data(v)


class PagamentoOut(BaseModel):
    """Pagamento do agendamento, espelhando o lançamento **ativo** do Caixa."""

    model_config = ConfigDict(extra="ignore")

    lancamentoId: str
    mes: str
    valorCentavos: int
    formaPagamento: Optional[str] = None
    dataPagamento: str


class AgendaOut(BaseModel):
    """Um agendamento. `novo` = pessoa ainda sem cadastro (`pacienteId` nulo).

    `pagamento` só vem quando há lançamento **ativo** no Caixa: cancelar o lançamento
    na tela de Caixa faz o "Pago" sumir da Agenda.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    data: str
    hora: str
    pacienteId: Optional[str] = None
    nome: str
    telefone: Optional[str] = None
    novo: bool
    profissionalId: Optional[str] = None
    profissional: Optional[str] = None  # nome de quem atende
    pagamento: Optional[PagamentoOut] = None
    criadoEm: Optional[str] = None
