"""Modelos Pydantic do Plano do aluno e da Tabela de preços (feature fluxo-caixa, F2).

O **plano** é o valor que aquele aluno paga por mês. Ele é a **fonte da verdade do
valor** — a Escala nunca é: a grade só sugere a frequência na hora de definir o plano, e
uma clínica que não usa a Escala tem a tela de mensalidades funcionando igual.

Diferença importante em relação ao lançamento: aqui **valor zero é válido**. Bolsista e
cortesia têm plano com `valorCentavos=0`, o que é diferente de "aluno sem plano" (quem
ainda não teve o valor definido). Os dois estados existem e aparecem diferentes na tela.

A **tabela de preços** é por frequência (1x/2x/3x/5x por semana → valor MENSAL). O "valor
por aula" nunca é digitado: é derivado na exibição (÷ 4,33 semanas). Quem cobra por aula
é a **aula avulsa** e a **reposição**, que têm preço próprio no nível da clínica.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

DIA_VENC_MIN = 1
DIA_VENC_MAX = 31
FREQ_MIN = 1
FREQ_MAX = 7

STATUS_SEM_PLANO = "sem_plano"
STATUS_ISENTO = "isento"
STATUS_PAGO = "pago"
STATUS_PARCIAL = "parcial"
STATUS_ABERTO = "aberto"


def _valida_centavos(v, campo: str):
    """Inteiro de centavos **>= 0** (zero é bolsista/cortesia, não erro).

    Mesma severidade do lançamento quanto ao tipo: float é recusado, não arredondado.
    """
    erro = ValueError(f"{campo} deve ser um número inteiro de centavos (0 ou mais)")
    if isinstance(v, bool) or isinstance(v, float):
        raise erro
    if isinstance(v, str):
        if not v.strip().isdigit():
            raise erro
        v = int(v.strip())
    if not isinstance(v, int) or v < 0:
        raise erro
    return v


class PlanoUpsert(BaseModel):
    """Payload de definição do plano (`PUT /financeiro/planos/{pacienteId}`)."""

    model_config = ConfigDict(extra="ignore")

    valorCentavos: int
    diaVencimento: Optional[int] = None
    frequencia: Optional[int] = None
    observacao: Optional[str] = None

    @field_validator("valorCentavos", mode="before")
    @classmethod
    def _valor(cls, v):
        return _valida_centavos(v, "valor")

    @field_validator("diaVencimento", mode="before")
    @classmethod
    def _dia(cls, v):
        if v is None or v == "":
            return None
        try:
            dia = int(v)
        except (TypeError, ValueError):
            raise ValueError("diaVencimento deve ser um número de 1 a 31")
        if dia < DIA_VENC_MIN or dia > DIA_VENC_MAX:
            raise ValueError("diaVencimento deve ser um número de 1 a 31")
        return dia

    @field_validator("frequencia", mode="before")
    @classmethod
    def _freq(cls, v):
        """Aulas por semana (1..7). Opcional — só serve para sugerir o valor da tabela."""
        if v is None or v == "":
            return None
        try:
            freq = int(v)
        except (TypeError, ValueError):
            raise ValueError("frequencia deve ser um número de 1 a 7 (aulas por semana)")
        if freq < FREQ_MIN or freq > FREQ_MAX:
            raise ValueError("frequencia deve ser um número de 1 a 7 (aulas por semana)")
        return freq

    @field_validator("observacao", mode="before")
    @classmethod
    def _obs(cls, v):
        if not isinstance(v, str):
            return None
        v = v.strip()
        if len(v) > 200:
            raise ValueError("observacao deve ter no máximo 200 caracteres")
        return v or None


class FaixaPreco(BaseModel):
    """Uma linha da tabela de preços: frequência → valor mensal."""

    model_config = ConfigDict(extra="ignore")

    frequencia: int
    valorCentavos: int

    @field_validator("frequencia", mode="before")
    @classmethod
    def _freq(cls, v):
        try:
            freq = int(v)
        except (TypeError, ValueError):
            raise ValueError("frequencia deve ser um número de 1 a 7 (aulas por semana)")
        if freq < FREQ_MIN or freq > FREQ_MAX:
            raise ValueError("frequencia deve ser um número de 1 a 7 (aulas por semana)")
        return freq

    @field_validator("valorCentavos", mode="before")
    @classmethod
    def _valor(cls, v):
        return _valida_centavos(v, "valor")


class ConfigPrecos(BaseModel):
    """Tabela de preços da clínica (`PUT /financeiro/config`).

    A clínica **não é obrigada** a preencher: a tela de mensalidades funciona com valor
    digitado direto no aluno. A tabela só existe para poupar digitação e dar consistência.
    """

    model_config = ConfigDict(extra="ignore")

    tabelaPrecos: list[FaixaPreco] = []
    aulaAvulsaCentavos: int = 0
    reposicaoCentavos: int = 0

    @field_validator("tabelaPrecos", mode="before")
    @classmethod
    def _tabela(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("tabelaPrecos deve ser uma lista")
        return v

    @field_validator("aulaAvulsaCentavos", "reposicaoCentavos", mode="before")
    @classmethod
    def _precos_avulsos(cls, v):
        if v is None or v == "":
            return 0
        return _valida_centavos(v, "valor")


class PlanoOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pacienteId: str
    valorCentavos: int
    diaVencimento: Optional[int] = None
    frequencia: Optional[int] = None
    observacao: Optional[str] = None
    criadoEm: Optional[str] = None
    atualizadoEm: Optional[str] = None


class MensalidadeAluno(BaseModel):
    """Uma linha da tela de mensalidades — o cruzamento aluno × plano × pago no mês."""

    model_config = ConfigDict(extra="ignore")

    pacienteId: str
    nome: str
    valorCentavos: int          # 0 quando não há plano
    pagoCentavos: int
    emAbertoCentavos: int
    diaVencimento: Optional[int] = None
    frequencia: Optional[int] = None      # do plano
    frequenciaEscala: Optional[int] = None  # quantos horários o aluno tem na grade
    divergenciaEscala: bool = False       # plano diz X, grade diz Y
    temPlano: bool = False
    status: str


class MensalidadesOut(BaseModel):
    """O mês inteiro de mensalidades: os três totais + a lista de alunos."""

    model_config = ConfigDict(extra="ignore")

    mes: str
    previstoCentavos: int
    recebidoCentavos: int
    emAbertoCentavos: int
    alunos: list[MensalidadeAluno]
