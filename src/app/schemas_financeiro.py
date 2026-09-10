"""Modelos Pydantic do Fluxo de Caixa (feature fluxo-caixa, FIN-01/05/12).

Um lançamento é uma entrada ou uma saída de dinheiro **que já aconteceu** (regime de
caixa). Ele vive na partição do mês da sua própria `data` — não do mês em que foi
digitado (ver `repository_financeiro.py`).

- `tipo` é `entrada` ou `saida`. **O sinal do dinheiro é o tipo**, nunca o valor.
- `valorCentavos` é **inteiro em centavos, sempre positivo**. Dinheiro nunca é float
  neste sistema: `0.1 + 0.2 != 0.3` em ponto flutuante, e um centavo perdido no total do
  mês destrói a confiança na tela inteira. Um float chegando aqui é sintoma de bug lá em
  cima, então ele é **rejeitado** em vez de arredondado em silêncio. String numérica
  (`"15000"`) é aceita porque é o que um JSON de front pode mandar.
- `data` é `AAAA-MM-DD` e precisa ser uma data **que existe** — `date.fromisoformat`
  barra `2026-02-30`, coisa que uma regex sozinha deixaria passar. A regex vem antes
  porque o `fromisoformat` do Python 3.11+ também aceita `20261005`, que não queremos.
- `competencia` (`AAAA-MM`) diz a que mês a **mensalidade** se refere e só faz sentido
  junto de `pacienteId` — é a preparação da F2 (histórico de pagamento por aluno). Os
  dois são opcionais e, quando ausentes, o item fica fora do GSI1 (índice esparso).
- Campos desconhecidos são ignorados (`extra="ignore"`).
"""
import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

TIPO_ENTRADA = "entrada"
TIPO_SAIDA = "saida"
TIPOS = (TIPO_ENTRADA, TIPO_SAIDA)

FORMAS_PAGAMENTO = ("dinheiro", "pix", "cartao", "transferencia")

DESCRICAO_MAX = 200

_RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _vazio_para_none(v):
    """Normaliza string: só-espaços/vazio → None; caso contrário, trimada."""
    if not isinstance(v, str):
        return v
    v = v.strip()
    return v or None


def valida_mes(mes: str) -> str:
    """Confere `AAAA-MM` e devolve normalizado. Usado no query/path param do router.

    Fica aqui (e não só no schema) porque o mês chega como parâmetro solto, fora de um
    corpo validado — o router converte a `ValueError` no mesmo 400 legível do resto.
    """
    if not isinstance(mes, str) or not _RE_MES.match(mes.strip()):
        raise ValueError("mes deve estar no formato AAAA-MM (ex.: 2026-10)")
    return mes.strip()


class LancamentoBase(BaseModel):
    """Campos comuns de criação/edição do lançamento."""

    model_config = ConfigDict(extra="ignore")

    tipo: str
    data: str
    valorCentavos: int
    descricao: str
    formaPagamento: Optional[str] = None
    pacienteId: Optional[str] = None
    competencia: Optional[str] = None

    @field_validator("tipo", mode="before")
    @classmethod
    def _valida_tipo(cls, v):
        if not isinstance(v, str) or v.strip().lower() not in TIPOS:
            raise ValueError("tipo deve ser 'entrada' ou 'saida'")
        return v.strip().lower()

    @field_validator("data", mode="before")
    @classmethod
    def _valida_data(cls, v):
        """`AAAA-MM-DD` que existe de verdade (barra 2026-02-30)."""
        if not isinstance(v, str) or not _RE_DATA.match(v.strip()):
            raise ValueError("data deve estar no formato AAAA-MM-DD (ex.: 2026-10-05)")
        limpa = v.strip()
        try:
            date.fromisoformat(limpa)
        except ValueError:
            raise ValueError("data não existe no calendário")
        return limpa

    @field_validator("valorCentavos", mode="before")
    @classmethod
    def _valida_valor(cls, v):
        """Inteiro de centavos > 0. Float é recusado (ver docstring do módulo)."""
        erro = ValueError("valor deve ser um número inteiro de centavos maior que zero")
        # bool é subclasse de int em Python — `True` viraria 1 centavo sem esta guarda.
        if isinstance(v, bool) or isinstance(v, float):
            raise erro
        if isinstance(v, str):
            if not v.strip().isdigit():
                raise erro
            v = int(v.strip())
        if not isinstance(v, int) or v <= 0:
            raise erro
        return v

    @field_validator("descricao", mode="before")
    @classmethod
    def _valida_descricao(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("descricao é obrigatória")
        limpa = v.strip()
        if len(limpa) > DESCRICAO_MAX:
            raise ValueError(f"descricao deve ter no máximo {DESCRICAO_MAX} caracteres")
        return limpa

    @field_validator("formaPagamento", mode="before")
    @classmethod
    def _valida_forma(cls, v):
        """Opcional; quando vem, tem que ser uma das formas conhecidas."""
        v = _vazio_para_none(v)
        if v is None:
            return None
        if v.lower() not in FORMAS_PAGAMENTO:
            raise ValueError(
                "formaPagamento deve ser " + ", ".join(FORMAS_PAGAMENTO)
            )
        return v.lower()

    @field_validator("pacienteId", mode="before")
    @classmethod
    def _limpa_paciente(cls, v):
        return _vazio_para_none(v)

    @field_validator("competencia", mode="before")
    @classmethod
    def _valida_competencia(cls, v):
        v = _vazio_para_none(v)
        if v is None:
            return None
        return valida_mes(v)

    @model_validator(mode="after")
    def _competencia_exige_paciente(self):
        """Competência é "de que mês é a mensalidade **do aluno**" — sem aluno não existe."""
        if self.competencia and not self.pacienteId:
            raise ValueError("competencia só pode ser informada junto com pacienteId")
        return self


class LancamentoCreate(LancamentoBase):
    """Payload de criação (`POST /financeiro/lancamentos`)."""


class LancamentoUpdate(LancamentoBase):
    """Payload de edição (`PUT /financeiro/lancamentos/{mes}/{id}`).

    Mesma forma da criação: a edição substitui os campos. Mudar a `data` para outro mês
    é recusado no router (`400`) — a data compõe a chave da partição.
    """


class LancamentoOut(BaseModel):
    """Representação de saída de um lançamento (uma linha do extrato)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    tipo: str
    data: str
    valorCentavos: int
    descricao: str
    formaPagamento: Optional[str] = None
    pacienteId: Optional[str] = None
    competencia: Optional[str] = None
    criadoEm: Optional[str] = None
    atualizadoEm: Optional[str] = None


class CaixaMesOut(BaseModel):
    """O caixa de um mês: os três totais + o extrato.

    Os totais vêm calculados do backend (e não somados no front) para que a tela e
    qualquer outro consumidor da API nunca discordem sobre o saldo.
    """

    model_config = ConfigDict(extra="ignore")

    mes: str
    entradasCentavos: int
    saidasCentavos: int
    saldoCentavos: int
    lancamentos: list[LancamentoOut]
