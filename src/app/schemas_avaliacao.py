"""Modelos Pydantic de Avaliação do paciente (feature avaliacao-pacientes, AVL-03/10).

Cadastro flexível (como paciente/aparelho): nenhum campo clínico é obrigatório.
- `data` opcional na entrada — o repositório assume hoje quando ausente; quando
  informada, deve estar em `YYYY-MM-DD`.
- Todos os textos vazios/só-espaços viram `None`.
- `avaliacaoPostural` e `medidas` são submodelos (MAP, AD-009); MAP sem nenhuma
  sub-chave preenchida vira `None` (não persiste objeto vazio).
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


def _vazio_para_none(v):
    """Normaliza string: só-espaços/vazio → None; caso contrário, trimada."""
    if not isinstance(v, str):
        return v
    v = v.strip()
    return v or None


class AvaliacaoPostural(BaseModel):
    """Observações da avaliação postural por vista (todos os campos opcionais)."""

    model_config = ConfigDict(extra="ignore")

    vistaAnterior: Optional[str] = None
    vistaLateralDireita: Optional[str] = None
    vistaLateralEsquerda: Optional[str] = None
    vistaPosterior: Optional[str] = None

    @field_validator("*", mode="before")
    @classmethod
    def _limpa(cls, v):
        return _vazio_para_none(v)


class Medidas(BaseModel):
    """Circunferências corporais em texto livre (todos os campos opcionais)."""

    model_config = ConfigDict(extra="ignore")

    braco: Optional[str] = None
    abdomen: Optional[str] = None
    coxa: Optional[str] = None
    panturrilha: Optional[str] = None

    @field_validator("*", mode="before")
    @classmethod
    def _limpa(cls, v):
        return _vazio_para_none(v)


class AvaliacaoBase(BaseModel):
    """Campos comuns de criação/edição da avaliação."""

    model_config = ConfigDict(extra="ignore")

    data: Optional[str] = None
    diagnosticoMedico: Optional[str] = None
    queixaPrincipal: Optional[str] = None
    hma: Optional[str] = None
    pressaoArterial: Optional[str] = None
    fc: Optional[str] = None
    avaliacaoPostural: Optional[AvaliacaoPostural] = None
    medidas: Optional[Medidas] = None
    inspecaoGeral: Optional[str] = None
    examesComplementares: Optional[str] = None
    observacao: Optional[str] = None

    @field_validator("data", mode="before")
    @classmethod
    def _valida_data(cls, v):
        """`data` opcional; quando informada, exige `YYYY-MM-DD`. Vazio → None."""
        if v is None:
            return None
        if not isinstance(v, str) or not v.strip():
            if isinstance(v, str):
                return None
            raise ValueError("data deve estar no formato YYYY-MM-DD")
        v = v.strip()
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("data deve estar no formato YYYY-MM-DD")
        return v

    @field_validator(
        "diagnosticoMedico",
        "queixaPrincipal",
        "hma",
        "pressaoArterial",
        "fc",
        "inspecaoGeral",
        "examesComplementares",
        "observacao",
        mode="before",
    )
    @classmethod
    def _texto_vazio_para_none(cls, v):
        return _vazio_para_none(v)

    @model_validator(mode="after")
    def _colapsa_maps_vazios(self):
        """MAP aninhado sem nenhuma sub-chave preenchida → None."""
        if self.avaliacaoPostural is not None and not any(
            self.avaliacaoPostural.model_dump().values()
        ):
            self.avaliacaoPostural = None
        if self.medidas is not None and not any(self.medidas.model_dump().values()):
            self.medidas = None
        return self


class AvaliacaoCreate(AvaliacaoBase):
    """Payload de criação (`POST /pacientes/{id}/avaliacoes`)."""


class AvaliacaoUpdate(AvaliacaoBase):
    """Payload de edição (`PUT /pacientes/{id}/avaliacoes/{avId}`)."""


class AvaliacaoOut(AvaliacaoBase):
    """Representação de saída da avaliação."""

    id: str
    pacienteId: str
    data: str
    ativo: bool = True
    criadoEm: str
    atualizadoEm: str
