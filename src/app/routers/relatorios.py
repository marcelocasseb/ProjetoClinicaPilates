"""Endpoints da aba Relatórios (feature relatorios, REL-01..22).

**Só admin**: o `require_admin` fica no `APIRouter`, como no Financeiro, então uma rota
nova acrescentada aqui já nasce protegida (D3). O `clinicId` vem do token
(`get_clinic_id`), nunca da requisição, e todo repositório é instanciado por clínica.

Cada endpoint só lê os dados e chama as funções puras de `app.relatorios`; as contas
ficam lá, testadas sem banco.
"""
import time
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import relatorios as rel
from app.deps import get_clinic_id, require_admin
from app.mensalidades import calcular_mensalidades
from app.repository import PacienteRepository
from app.repository_agenda import MESES_RETENCAO, AgendaRepository
from app.repository_atendimento import list_sessoes_periodo
from app.repository_escala import EscalaRepository
from app.repository_financeiro import FinanceiroRepository
from app.repository_plano import PlanoRepository
from app.repository_profissional import ProfissionalRepository
from app.schemas_financeiro import valida_mes
from app.schemas_relatorio import (
    RelAlunosOut,
    RelAtendimentoOut,
    RelFinanceiroOut,
    RelOcupacaoOut,
    RelRelacaoAlunosOut,
    RelSemanaOut,
)

router = APIRouter(
    prefix="/relatorios",
    tags=["relatorios"],
    dependencies=[Depends(require_admin)],  # REL-01: barra não-admin (403) em TODAS as rotas
)


def _400(msg: str):
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


def _mes(mes) -> str:
    """Mês do relatório: ausente = mês corrente (Brasília); inválido ou futuro = 400."""
    atual = rel.hoje_local().strftime("%Y-%m")
    if not mes:
        return atual
    try:
        mes = valida_mes(mes)
    except ValueError as e:
        raise _400(str(e))
    if mes > atual:
        raise _400("Não há relatório de mês futuro.")
    return mes


def _segunda(inicio) -> str:
    """Segunda-feira da semana: ausente = semana atual; inválida, não-segunda ou futura = 400."""
    atual = rel.segunda_da_semana(rel.hoje_local().isoformat())
    if not inicio:
        return atual
    try:
        d = date.fromisoformat(inicio)
    except ValueError:
        raise _400("inicio deve ser uma data AAAA-MM-DD.")
    if d.weekday() != 0:
        raise _400("inicio deve ser uma segunda-feira.")
    if d.isoformat() > atual:
        raise _400("Não há relatório de semana futura.")
    return d.isoformat()


@router.get("/financeiro", response_model=RelFinanceiroOut)
def relatorio_financeiro(
    mes: str = Query(default=None, description="AAAA-MM; ausente = mês corrente"),
    clinic_id: str = Depends(get_clinic_id),
) -> dict:
    """Caixa do mês e dos 12 meses, receita por forma, mensalidades e extrato.

    Custo: 12 Queries do Caixa (uma por mês) + 4 das mensalidades.
    """
    mes = _mes(mes)
    fin = FinanceiroRepository(clinic_id)
    por_mes = {m: fin.list_mes(m) for m in rel.meses_ate(mes)}
    lancs = por_mes[mes]
    mensalidades = calcular_mensalidades(
        mes,
        PacienteRepository(clinic_id).list_ativos(),
        PlanoRepository(clinic_id).list_all(),
        fin.list_por_competencia(mes),
        EscalaRepository(clinic_id).list_all(),
    )
    return {
        "mes": mes,
        "caixa": rel.resumo_caixa(lancs),
        "evolucao": [{"mes": m, **rel.resumo_caixa(l)} for m, l in por_mes.items()],
        "porForma": rel.receita_por_forma(lancs),
        "mensalidades": rel.resumo_mensalidades(mensalidades),
        "extrato": rel.extrato(lancs),
    }


@router.get("/alunos", response_model=RelAlunosOut)
def relatorio_alunos(
    mes: str = Query(default=None, description="AAAA-MM; ausente = mês corrente"),
    clinic_id: str = Depends(get_clinic_id),
) -> dict:
    mes = _mes(mes)
    perfis = PacienteRepository(clinic_id).list_todos()
    ativos = [p for p in perfis if p.get("ativo", True)]
    return {
        "mes": mes,
        **rel.indicadores_alunos(perfis, mes),
        "evolucao": rel.evolucao_alunos(perfis, rel.meses_ate(mes)),
        "carteira": rel.carteira_planos(PlanoRepository(clinic_id).list_all(), ativos),
    }


@router.get("/relacao-alunos", response_model=RelRelacaoAlunosOut)
def relatorio_relacao_alunos(clinic_id: str = Depends(get_clinic_id)) -> dict:
    """Alunos ativos de hoje (sem mês): contato, plano e horários na escala."""
    alunos = rel.relacao_alunos(
        PacienteRepository(clinic_id).list_ativos(),
        PlanoRepository(clinic_id).list_all(),
        EscalaRepository(clinic_id).list_all(),
    )
    return {"total": len(alunos), "alunos": alunos}


@router.get("/ocupacao", response_model=RelOcupacaoOut)
def relatorio_ocupacao(clinic_id: str = Depends(get_clinic_id)) -> dict:
    """Ocupação da grade atual (a escala não guarda histórico, então não há mês)."""
    return rel.ocupacao(
        EscalaRepository(clinic_id).list_all(),
        PacienteRepository(clinic_id).list_ativos(),
    )


@router.get("/atendimento", response_model=RelAtendimentoOut)
def relatorio_atendimento(
    mes: str = Query(default=None, description="AAAA-MM; ausente = mês corrente"),
    clinic_id: str = Depends(get_clinic_id),
) -> dict:
    """Aulas registradas (Pilates) e marcações da Agenda, separadas, no mês e em 12 meses.

    As aulas são lidas aluno a aluno, em paralelo (`repository_atendimento`); a Agenda sai
    de 1 Query paginada. Inclui alunos removidos: a aula deles aconteceu.
    """
    mes = _mes(mes)
    meses = rel.meses_ate(mes)
    de, ate = f"{meses[0]}-01", rel.ultimo_dia(mes)
    perfis = PacienteRepository(clinic_id).list_todos()
    sessoes = list_sessoes_periodo(clinic_id, [p["id"] for p in perfis], de, ate)
    agenda = AgendaRepository(clinic_id).list_periodo(de, ate)
    profissionais = {p["id"]: p.get("nome") or "" for p in ProfissionalRepository(clinic_id).list_todos()}
    disponiveis = rel.meses_agenda_disponiveis(meses, int(time.time()))
    return {
        **rel.atendimento(sessoes, agenda, perfis, profissionais, mes, meses, disponiveis),
        "agendaRetencaoMeses": MESES_RETENCAO,
    }


@router.get("/semana", response_model=RelSemanaOut)
def relatorio_semana(
    inicio: str = Query(default=None, description="Segunda-feira AAAA-MM-DD; ausente = semana atual"),
    clinic_id: str = Depends(get_clinic_id),
) -> dict:
    """Quem passou na semana: aulas registradas e marcações da Agenda, por dia."""
    inicio = _segunda(inicio)
    fim = (date.fromisoformat(inicio) + timedelta(days=6)).isoformat()
    perfis = PacienteRepository(clinic_id).list_todos()
    sessoes = list_sessoes_periodo(clinic_id, [p["id"] for p in perfis], inicio, fim)
    disponivel = rel.agenda_disponivel_desde(inicio, int(time.time()))
    agenda = AgendaRepository(clinic_id).list_periodo(inicio, fim) if disponivel else []
    return rel.semana(sessoes, agenda, perfis, inicio, disponivel)
