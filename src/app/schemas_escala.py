"""Modelos Pydantic da Escala Semanal (feature escala, ESC-03/07).

Uma matrícula é o par **aluno + dia da semana + horário** — a grade fixa da clínica
("Rebecca vem segunda e quarta às 7h"). Não é um agendamento datado: vale toda semana
até alguém mudar.

- `dia` é inteiro **1..7** no padrão ISO (1 = segunda … 7 = domingo).
- `hora` é `HH:MM` 24h **com zero à esquerda** (`07:00`, não `7:00`). O zero não é
  estética: a hora entra no SK do DynamoDB, e só zerada à esquerda a ordem alfabética
  do SK coincide com a ordem cronológica da grade.
- `pacienteId` é obrigatório; o vínculo com um aluno ativo da clínica é conferido no
  router (404), não aqui.
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# 00:00 … 23:59, sempre com dois dígitos em cada lado.
_RE_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

DIA_MIN = 1
DIA_MAX = 7


class EscalaCreate(BaseModel):
    """Payload de matrícula (`POST /escala`)."""

    model_config = ConfigDict(extra="ignore")

    dia: int
    hora: str
    pacienteId: str

    @field_validator("dia", mode="before")
    @classmethod
    def _valida_dia(cls, v):
        """Aceita 1..7 (e a string equivalente, que é como o path param chega)."""
        try:
            dia = int(v)
        except (TypeError, ValueError):
            raise ValueError("dia deve ser um número de 1 (segunda) a 7 (domingo)")
        if dia < DIA_MIN or dia > DIA_MAX:
            raise ValueError("dia deve ser um número de 1 (segunda) a 7 (domingo)")
        return dia

    @field_validator("hora", mode="before")
    @classmethod
    def _valida_hora(cls, v):
        """Exige `HH:MM` 24h com zero à esquerda (ver docstring do módulo)."""
        if not isinstance(v, str) or not _RE_HORA.match(v.strip()):
            raise ValueError("hora deve estar no formato HH:MM (ex.: 07:00)")
        return v.strip()

    @field_validator("pacienteId", mode="before")
    @classmethod
    def _valida_paciente(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("pacienteId é obrigatório")
        return v.strip()


class EscalaOut(BaseModel):
    """Representação de saída da matrícula (uma célula da grade).

    `nome` é resolvido **ao vivo** pelo router a partir do cadastro de pacientes —
    o snapshot `pacienteNome` gravado no item serve só de fallback (ver spec, ESC-09).
    """

    model_config = ConfigDict(extra="ignore")

    dia: int
    hora: str
    pacienteId: str
    nome: str
    criadoEm: Optional[str] = None
