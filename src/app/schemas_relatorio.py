"""Contrato de saída dos relatórios (`GET /relatorios/*`).

Os números saem prontos de `app.relatorios`; estes modelos só fixam o formato que o
front consome. Valores em centavos inteiros. `None` na Agenda = "sem dados" (retenção).
"""
from typing import Optional

from pydantic import BaseModel

# --- Financeiro -------------------------------------------------------------


class CaixaResumo(BaseModel):
    entradasCentavos: int
    saidasCentavos: int
    saldoCentavos: int


class CaixaMes(CaixaResumo):
    mes: str


class ReceitaForma(BaseModel):
    forma: str
    valorCentavos: int
    pct: float


class MensalidadesResumo(BaseModel):
    previstoCentavos: int
    recebidoCentavos: int
    emAbertoCentavos: int
    porStatus: dict[str, int]


class LinhaExtrato(BaseModel):
    data: str
    descricao: str
    formaPagamento: Optional[str] = None
    tipo: str
    valorCentavos: int


class RelFinanceiroOut(BaseModel):
    mes: str  # mês em que o período termina (o das mensalidades)
    de: str
    ate: str
    caixa: CaixaResumo
    evolucao: list[CaixaMes]
    porForma: list[ReceitaForma]
    mensalidades: MensalidadesResumo
    extrato: list[LinhaExtrato]


# --- Alunos -----------------------------------------------------------------


class AlunoNovo(BaseModel):
    id: str
    nome: str
    criadoEm: str


class AlunosMes(BaseModel):
    mes: str
    ativos: int
    novos: int
    saidas: int


class FaixaFrequencia(BaseModel):
    frequencia: Optional[int] = None
    alunos: int


class Carteira(BaseModel):
    totalMensalCentavos: int
    ticketMedioCentavos: int
    comPlano: int
    isentos: int
    semPlano: int
    porFrequencia: list[FaixaFrequencia]


class RelAlunosOut(BaseModel):
    mes: str
    de: str
    ate: str
    ativosFimMes: int
    novos: int
    saidas: int
    evolucao: list[AlunosMes]
    carteira: Carteira
    novosLista: list[AlunoNovo]


class PlanoRelacao(BaseModel):
    valorCentavos: int
    frequencia: Optional[int] = None
    diaVencimento: Optional[int] = None


class AlunoRelacao(BaseModel):
    id: str
    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    dataNascimento: Optional[str] = None
    plano: Optional[PlanoRelacao] = None
    isento: bool
    horarios: list[str]


class RelRelacaoAlunosOut(BaseModel):
    total: int
    alunos: list[AlunoRelacao]


# --- Ocupação ---------------------------------------------------------------


class Celula(BaseModel):
    dia: int
    hora: str
    alunos: int


class AlunoRef(BaseModel):
    id: str
    nome: str


class RelOcupacaoOut(BaseModel):
    celulas: list[Celula]
    matriculas: int
    alunosDistintos: int
    mediaPorHorarioOcupado: float
    top5: list[Celula]
    foraDaEscala: list[AlunoRef]


# --- Atendimento e semana ---------------------------------------------------


class AtendimentoMes(BaseModel):
    mes: str
    aulas: int
    agenda: Optional[int] = None


class PorProfissional(BaseModel):
    profissionalId: Optional[str] = None
    nome: str
    aulas: int
    agenda: Optional[int] = None


class PorAluno(BaseModel):
    pacienteId: Optional[str] = None
    nome: str
    novo: bool
    aulas: int
    agenda: Optional[int] = None


class ItemRanking(BaseModel):
    nome: str
    aulas: int


class RelAtendimentoOut(BaseModel):
    de: str
    ate: str
    totalAulas: int
    totalAgenda: Optional[int] = None
    agendaDesde: Optional[str] = None
    agendaRetencaoMeses: int
    evolucao: list[AtendimentoMes]
    porProfissional: list[PorProfissional]
    porAluno: list[PorAluno]
    aparelhos: list[ItemRanking]
    treinos: list[ItemRanking]


class DiaSemana(BaseModel):
    aula: int
    agenda: int


class AlunoSemana(BaseModel):
    pacienteId: Optional[str] = None
    nome: str
    novo: bool
    dias: dict[str, DiaSemana]
    total: int


class RelSemanaOut(BaseModel):
    inicio: str
    fim: str
    agendaDisponivel: bool
    agendaDesde: Optional[str] = None
    distintos: int
    totalAulas: int
    totalAgenda: int
    alunos: list[AlunoSemana]
