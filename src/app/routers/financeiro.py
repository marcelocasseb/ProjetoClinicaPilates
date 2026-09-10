"""Endpoints do Fluxo de Caixa — livro-caixa mensal da clínica (feature fluxo-caixa).

Rotas de **nível clínica** (`/financeiro`, como `/aparelhos` e `/escala`), multi-tenant
(AD-007): o `clinicId` vem de `get_clinic_id` (deps.py), nunca do corpo da requisição.

**Só admin.** O `require_admin` é declarado **no `APIRouter`**, não rota a rota: faturamento
é dado sensível, e uma rota nova acrescentada aqui amanhã nasce protegida sem ninguém
precisar lembrar de repetir a dependência (FIN-06).

Os três totais do mês são calculados **aqui**, e não somados no front, para que a tela e
qualquer outro consumidor da API nunca discordem sobre o saldo.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_clinic_id, require_admin
from app.repository import PacienteRepository
from app.repository_escala import EscalaRepository
from app.repository_financeiro import FinanceiroRepository, mes_da_data
from app.repository_plano import PlanoRepository
from app.schemas_financeiro import (
    TIPO_ENTRADA,
    CaixaMesOut,
    LancamentoCreate,
    LancamentoOut,
    LancamentoUpdate,
    valida_mes,
)
from app.schemas_plano import (
    STATUS_ABERTO,
    STATUS_ISENTO,
    STATUS_PAGO,
    STATUS_PARCIAL,
    STATUS_SEM_PLANO,
    ConfigPrecos,
    MensalidadesOut,
    PlanoOut,
    PlanoUpsert,
)

router = APIRouter(
    prefix="/financeiro",
    tags=["financeiro"],
    dependencies=[Depends(require_admin)],  # FIN-06: barra não-admin (403) em TODAS as rotas
)


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> FinanceiroRepository:
    return FinanceiroRepository(clinic_id=clinic_id)


def get_planos(clinic_id: str = Depends(get_clinic_id)) -> PlanoRepository:
    return PlanoRepository(clinic_id=clinic_id)


def get_pacientes(clinic_id: str = Depends(get_clinic_id)) -> PacienteRepository:
    return PacienteRepository(clinic_id=clinic_id)


def get_escala(clinic_id: str = Depends(get_clinic_id)) -> EscalaRepository:
    return EscalaRepository(clinic_id=clinic_id)


def _mes_corrente() -> str:
    """Mês corrente em UTC — só o *fallback* de quando o front não manda `mes`.

    O front sempre envia o mês que está exibindo (calculado no fuso do navegador), então
    a diferença de fuso não aparece na tela; isto aqui existe para a API ser utilizável
    sem parâmetro (`GET /financeiro/lancamentos`).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _validar_mes(mes: str) -> str:
    """Valida o `mes` de query/path param e converte a falha no 400 legível do projeto.

    O handler global de `main.py` só alcança erros de validação do **corpo**; parâmetro
    solto precisa desta conversão à mão (mesmo padrão de `routers/escala.py`).
    """
    try:
        return valida_mes(mes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/lancamentos", response_model=CaixaMesOut)
def caixa_do_mes(
    mes: str = Query(default=None, description="AAAA-MM; ausente = mês corrente"),
    repo: FinanceiroRepository = Depends(get_repository),
) -> dict:
    """Extrato do mês + entradas, saídas e saldo (FIN-03, FIN-04).

    Mês sem movimento devolve `200` com lista vazia e totais zerados — mês parado é um
    fato, não um erro.
    """
    mes = _validar_mes(mes) if mes else _mes_corrente()
    lancamentos = repo.list_mes(mes)

    entradas = sum(l["valorCentavos"] for l in lancamentos if l["tipo"] == TIPO_ENTRADA)
    saidas = sum(l["valorCentavos"] for l in lancamentos if l["tipo"] != TIPO_ENTRADA)

    return {
        "mes": mes,
        "entradasCentavos": entradas,
        "saidasCentavos": saidas,
        "saldoCentavos": entradas - saidas,
        "lancamentos": lancamentos,
    }


@router.post("/lancamentos", response_model=LancamentoOut, status_code=status.HTTP_201_CREATED)
def criar_lancamento(
    payload: LancamentoCreate,
    repo: FinanceiroRepository = Depends(get_repository),
) -> dict:
    """Registra uma entrada ou saída (FIN-01).

    A partição é a do mês da **`data` informada**, não a de hoje: uma conta de setembro
    lançada em outubro pertence a setembro.
    """
    return repo.create(payload.model_dump())


@router.put("/lancamentos/{mes}/{lancamento_id}", response_model=LancamentoOut)
def editar_lancamento(
    mes: str,
    lancamento_id: str,
    payload: LancamentoUpdate,
    repo: FinanceiroRepository = Depends(get_repository),
) -> dict:
    """Corrige um lançamento (FIN-10).

    `400` se a `data` nova for de **outro mês**: a competência compõe a chave da partição,
    então mudar de mês é cancelar aqui e relançar lá — e é bom que seja explícito, porque
    isso mexe no fechamento de dois meses de uma vez.
    """
    mes = _validar_mes(mes)
    if mes_da_data(payload.data) != mes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data pertence a outro mês. Cancele este lançamento e registre no mês correto.",
        )

    alterado = repo.update(mes, lancamento_id, payload.model_dump())
    if alterado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado"
        )
    return alterado


@router.delete("/lancamentos/{mes}/{lancamento_id}")
def cancelar_lancamento(
    mes: str,
    lancamento_id: str,
    repo: FinanceiroRepository = Depends(get_repository),
) -> dict:
    """Cancela o lançamento (FIN-11) — soft delete: some da tela, fica na auditoria."""
    mes = _validar_mes(mes)
    if not repo.soft_delete(mes, lancamento_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado"
        )
    return {"detail": "Lançamento cancelado"}


# ---------------------------------------------------------------------------
# F2 — Mensalidades, planos e tabela de preços
# ---------------------------------------------------------------------------


def _status(tem_plano: bool, valor: int, pago: int) -> str:
    """Situação da mensalidade do aluno no mês.

    "Sem plano" e "isento" são estados **diferentes**: o primeiro é alguém que ninguém
    definiu quanto paga (precisa de ação); o segundo é bolsista/cortesia (está resolvido).
    Tratar os dois como "R$ 0,00" esconderia trabalho pendente.
    """
    if not tem_plano:
        return STATUS_SEM_PLANO
    if valor == 0:
        return STATUS_ISENTO
    if pago >= valor:
        return STATUS_PAGO
    if pago > 0:
        return STATUS_PARCIAL
    return STATUS_ABERTO


@router.get("/mensalidades", response_model=MensalidadesOut)
def mensalidades_do_mes(
    mes: str = Query(default=None, description="AAAA-MM; ausente = mês corrente"),
    repo: FinanceiroRepository = Depends(get_repository),
    planos: PlanoRepository = Depends(get_planos),
    pacientes: PacienteRepository = Depends(get_pacientes),
    escala: EscalaRepository = Depends(get_escala),
) -> dict:
    """Previsto × recebido × em aberto do mês, aluno a aluno (FIN-13..17).

    A lista sai do **cadastro de pacientes**, não da escala: numa clínica que não usa a
    grade, esta tela funciona igual. A escala entra só para apontar **divergência**
    ("o plano diz 2x por semana, mas ele está em 3 horários").

    Custo: 4 Queries no total (alunos, planos, pagamentos da competência, grade) —
    nenhuma delas por aluno.
    """
    mes = _validar_mes(mes) if mes else _mes_corrente()

    alunos = pacientes.list_ativos()
    por_paciente = {p["pacienteId"]: p for p in planos.list_all()}

    # Pagos: 1 Query no GSI1 por competência, alcançando qualquer partição mensal
    # (a mensalidade de setembro paga em outubro conta para setembro).
    pago_por_aluno: dict[str, int] = {}
    for lanc in repo.list_por_competencia(mes):
        if lanc.get("tipo") != TIPO_ENTRADA:
            continue
        pid = lanc.get("pacienteId")
        pago_por_aluno[pid] = pago_por_aluno.get(pid, 0) + lanc["valorCentavos"]

    # Quantos horários cada aluno ocupa na grade (0 se a clínica não usa a Escala).
    horarios_por_aluno: dict[str, int] = {}
    for m in escala.list_all():
        pid = m["pacienteId"]
        horarios_por_aluno[pid] = horarios_por_aluno.get(pid, 0) + 1

    linhas = []
    previsto = recebido = em_aberto = 0
    for p in alunos:
        pid = p["id"]
        plano = por_paciente.get(pid)
        tem_plano = plano is not None
        valor = int(plano.get("valorCentavos") or 0) if tem_plano else 0
        pago = pago_por_aluno.get(pid, 0)
        # Em aberto é somado **por aluno**: se um pagou a mais, isso não pode mascarar
        # a dívida de outro no total da clínica.
        aberto = max(0, valor - pago)
        freq_plano = plano.get("frequencia") if tem_plano else None
        freq_escala = horarios_por_aluno.get(pid)

        previsto += valor
        recebido += pago
        em_aberto += aberto

        linhas.append(
            {
                "pacienteId": pid,
                "nome": p.get("nome") or "",
                "valorCentavos": valor,
                "pagoCentavos": pago,
                "emAbertoCentavos": aberto,
                "diaVencimento": plano.get("diaVencimento") if tem_plano else None,
                "frequencia": freq_plano,
                "frequenciaEscala": freq_escala,
                "divergenciaEscala": bool(
                    freq_plano and freq_escala and freq_plano != freq_escala
                ),
                "temPlano": tem_plano,
                "status": _status(tem_plano, valor, pago),
            }
        )

    linhas.sort(key=lambda l: l["nome"].lower())
    return {
        "mes": mes,
        "previstoCentavos": previsto,
        "recebidoCentavos": recebido,
        "emAbertoCentavos": em_aberto,
        "alunos": linhas,
    }


@router.put("/planos/{paciente_id}", response_model=PlanoOut)
def definir_plano(
    paciente_id: str,
    payload: PlanoUpsert,
    planos: PlanoRepository = Depends(get_planos),
    pacientes: PacienteRepository = Depends(get_pacientes),
) -> dict:
    """Define quanto o aluno paga por mês (FIN-13). `404` se o aluno não é da clínica."""
    if pacientes.get(paciente_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")
    return planos.upsert(paciente_id, payload.model_dump())


@router.delete("/planos/{paciente_id}")
def remover_plano(
    paciente_id: str,
    planos: PlanoRepository = Depends(get_planos),
) -> dict:
    """Tira o plano do aluno — ele volta a aparecer como "sem plano" na tela."""
    if not planos.delete(paciente_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado")
    return {"detail": "Plano removido"}


@router.get("/config", response_model=ConfigPrecos)
def obter_config(planos: PlanoRepository = Depends(get_planos)) -> dict:
    """Tabela de preços da clínica. Nunca 404: não configurado devolve os padrões zerados."""
    return planos.get_config()


@router.put("/config", response_model=ConfigPrecos)
def salvar_config(
    payload: ConfigPrecos,
    planos: PlanoRepository = Depends(get_planos),
) -> dict:
    """Salva a tabela de preços por frequência + aula avulsa e reposição (FIN-16)."""
    return planos.set_config(payload.model_dump())
