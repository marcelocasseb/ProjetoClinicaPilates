"""Modelos Pydantic de Sessão/Aula de Pilates (feature registro-sessoes, SES-03/10).

Uma aula pende do paciente (histórico datado). Diferente das outras entidades, a aula
tem um campo **obrigatório**: `aparelhos` (lista com ≥1 item). Cada aparelho é um snapshot
`{aparelhoId, nome, treinos[]}` copiado no momento do registro — o histórico fica imune a
edição/remoção posterior do aparelho no catálogo.

- `data` opcional na entrada — o repositório assume hoje quando ausente; quando informada,
  deve estar em `YYYY-MM-DD`.
- `nome` do aparelho é obrigatório (é o que aparece no histórico); só-espaços é rejeitado.
- `treinos` é livre (lista de textos vinda da lista fixa do front); itens vazios são descartados.
- Textos gerais (`profissional`, `observacao`) vazios/só-espaços viram `None`.
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


def _vazio_para_none(v):
    """Normaliza string: só-espaços/vazio → None; caso contrário, trimada."""
    if not isinstance(v, str):
        return v
    v = v.strip()
    return v or None


class AparelhoSessao(BaseModel):
    """Aparelho usado na aula (snapshot) com seus tipos de treino."""

    model_config = ConfigDict(extra="ignore")

    aparelhoId: Optional[str] = None
    nome: str
    treinos: list[str] = []

    @field_validator("aparelhoId", mode="before")
    @classmethod
    def _limpa_id(cls, v):
        return _vazio_para_none(v)

    @field_validator("nome", mode="before")
    @classmethod
    def _valida_nome(cls, v):
        """`nome` é obrigatório e não pode ser vazio/só-espaços (vai pro histórico)."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("nome do aparelho é obrigatório")
        return v.strip()

    @field_validator("treinos", mode="before")
    @classmethod
    def _limpa_treinos(cls, v):
        """Aceita None → []; descarta itens vazios; trima cada treino."""
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("treinos deve ser uma lista")
        limpos = []
        for t in v:
            if isinstance(t, str) and t.strip():
                limpos.append(t.strip())
        return limpos


class SessaoBase(BaseModel):
    """Campos comuns de criação/edição da aula."""

    model_config = ConfigDict(extra="ignore")

    data: Optional[str] = None
    profissional: Optional[str] = None
    observacao: Optional[str] = None
    aparelhos: list[AparelhoSessao]

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

    @field_validator("profissional", "observacao", mode="before")
    @classmethod
    def _texto_vazio_para_none(cls, v):
        return _vazio_para_none(v)

    @field_validator("aparelhos", mode="before")
    @classmethod
    def _exige_aparelho(cls, v):
        """Uma aula precisa de ao menos um aparelho (SES-06/10)."""
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("uma aula precisa de ao menos um aparelho")
        return v


class SessaoCreate(SessaoBase):
    """Payload de criação (`POST /pacientes/{id}/sessoes`)."""


class SessaoUpdate(SessaoBase):
    """Payload de edição (`PUT /pacientes/{id}/sessoes/{sessaoId}`)."""


class SessaoOut(SessaoBase):
    """Representação de saída da aula."""

    id: str
    pacienteId: str
    data: str
    ativo: bool = True
    criadoEm: str
    atualizadoEm: str
