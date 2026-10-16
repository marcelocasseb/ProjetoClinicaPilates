"""Endpoints da Agenda — marcações datadas da clínica (feature agenda).

Rotas de **nível clínica** (`/agenda`, como `/escala`), multi-tenant (AD-007): o
`clinicId` vem de `get_clinic_id` (deps.py), nunca do corpo da requisição.

A Agenda é independente da Escala: a Escala é a grade fixa da semana, a Agenda é
"quem vem em tal data". Quem vem é um paciente cadastrado **ou** uma pessoa ainda sem
cadastro (nome + telefone), que depois pode ser vinculada a um paciente.

Para cadastrados, o `GET` usa o nome/telefone **ao vivo** do cadastro e descarta
agendamentos de pacientes removidos (mesma auto-limpeza da Escala, ESC-09).
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from app.deps import get_clinic_id
from app.repository import PacienteRepository
from app.repository_agenda import AgendaRepository
from app.repository_financeiro import FinanceiroRepository, mes_da_data
from app.schemas_agenda import (
    AgendaCreate,
    AgendaOut,
    AgendaPagamento,
    AgendaVincular,
    valida_data,
    valida_hora,
)
from app.schemas_financeiro import TIPO_ENTRADA, LancamentoCreate

router = APIRouter(prefix="/agenda", tags=["agenda"])

# Período máximo de um GET: folga para um mês inteiro de calendário (6 semanas).
PERIODO_MAX_DIAS = 62

JA_PAGO = "Este agendamento já está pago"


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> AgendaRepository:
    return AgendaRepository(clinic_id=clinic_id)


def get_pacientes(clinic_id: str = Depends(get_clinic_id)) -> PacienteRepository:
    return PacienteRepository(clinic_id=clinic_id)


# Caixa SEM `require_admin`: receber o agendamento é trabalho da recepção (qualquer
# papel). O que continua só de admin é VER o caixa — as rotas de /financeiro.
def get_financeiro(clinic_id: str = Depends(get_clinic_id)) -> FinanceiroRepository:
    return FinanceiroRepository(clinic_id=clinic_id)


def _validar(fn, valor: str) -> str:
    """Valida query/path params com as regras do schema → 400 com mensagem legível.

    O handler global de `main.py` só alcança erros de validação do **corpo**.
    """
    try:
        return fn(valor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _pagamento_vivo(item: dict, lanc: Optional[dict]) -> Optional[dict]:
    """O pagamento como o Caixa o vê agora: valor/forma/data do lançamento **ativo**.

    Lançamento cancelado (ou editado) na tela de Caixa vale mais que a cópia guardada
    na marcação — sem lançamento ativo, não há "Pago".
    """
    pag = item.get("pagamento")
    if not pag or lanc is None:
        return None
    return {
        "lancamentoId": lanc["id"],
        "mes": pag["mes"],
        "valorCentavos": lanc["valorCentavos"],
        "formaPagamento": lanc.get("formaPagamento"),
        "dataPagamento": lanc["data"],
    }


def _lancamento_do(item: dict, fin: FinanceiroRepository) -> Optional[dict]:
    pag = item.get("pagamento")
    return fin.get(pag["mes"], pag["lancamentoId"]) if pag else None


def _saida(item: dict, nome: str, telefone=None, lanc: Optional[dict] = None) -> dict:
    return {
        **item,
        "nome": nome,
        "telefone": telefone if item.get("pacienteId") else item.get("telefone"),
        "novo": not item.get("pacienteId"),
        "pagamento": _pagamento_vivo(item, lanc),
    }


def _buscar(repo: AgendaRepository, data: str, hora: str, agenda_id: str) -> dict:
    item = repo.get(data, hora, agenda_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento não encontrado")
    return item


@router.get("", response_model=list[AgendaOut])
def listar_agenda(
    de: str = Query(...),
    ate: str = Query(...),
    repo: AgendaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
    fin: FinanceiroRepository = Depends(get_financeiro),
) -> list[dict]:
    """Agendamentos de `de` a `ate` (inclusive), ordenados por data → hora → nome.

    O "Pago" é conferido contra o Caixa: 1 Query por mês de pagamento envolvido
    (normalmente 1), não uma leitura por agendamento.
    """
    de = _validar(valida_data, de)
    ate = _validar(valida_data, ate)
    dias = (date.fromisoformat(ate) - date.fromisoformat(de)).days
    if dias < 0:
        raise HTTPException(status_code=400, detail="a data final deve ser igual ou depois da inicial")
    if dias >= PERIODO_MAX_DIAS:
        raise HTTPException(status_code=400, detail=f"período máximo de {PERIODO_MAX_DIAS} dias")

    itens = repo.list_periodo(de, ate)
    ativos = {}
    if any(i.get("pacienteId") for i in itens):
        ativos = {p["id"]: p for p in pacientes.list_ativos()}

    meses = {i["pagamento"]["mes"] for i in itens if i.get("pagamento")}
    lancs = {l["id"]: l for mes in meses for l in fin.list_mes(mes)}

    saida = []
    for i in itens:
        pid = i.get("pacienteId")
        lanc = lancs.get((i.get("pagamento") or {}).get("lancamentoId"))
        if pid is None:
            saida.append(_saida(i, i.get("nome") or "", lanc=lanc))
        elif pid in ativos:
            p = ativos[pid]
            nome = p.get("nome") or i.get("nome") or ""
            saida.append(_saida(i, nome, p.get("telefone"), lanc))
    saida.sort(key=lambda a: (a["data"], a["hora"], a["nome"].lower()))
    return saida


@router.post("", response_model=AgendaOut, status_code=status.HTTP_201_CREATED)
def agendar(
    payload: AgendaCreate,
    repo: AgendaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
) -> dict:
    """Marca um paciente cadastrado ou uma pessoa nova numa data+hora.

    `404` se o paciente não existe/foi removido/é de outra clínica; `409` se ele já
    está marcado nesse mesmo dia e horário.
    """
    if payload.pacienteId:
        paciente = pacientes.get(payload.pacienteId)
        if paciente is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")
        if repo.paciente_no_horario(payload.data, payload.hora, payload.pacienteId):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Este aluno já está marcado neste horário"
            )
        nome = paciente.get("nome") or ""
        criado = repo.create(payload.data, payload.hora, payload.pacienteId, nome, None)
        return _saida(criado, nome, paciente.get("telefone"))

    criado = repo.create(payload.data, payload.hora, None, payload.nome, payload.telefone)
    return _saida(criado, payload.nome)


@router.put("/{data}/{hora}/{agenda_id}", response_model=AgendaOut)
def vincular(
    data: str,
    hora: str,
    agenda_id: str,
    payload: AgendaVincular,
    repo: AgendaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
    fin: FinanceiroRepository = Depends(get_financeiro),
) -> dict:
    """Liga a marcação de uma pessoa nova ao paciente recém-cadastrado.

    `404` se o paciente ou a marcação não existem, ou se a marcação já é de um paciente.
    """
    data = _validar(valida_data, data)
    hora = _validar(valida_hora, hora)
    paciente = pacientes.get(payload.pacienteId)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")
    nome = paciente.get("nome") or ""
    atualizado = repo.vincular(data, hora, agenda_id, payload.pacienteId, nome)
    if atualizado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento não encontrado"
        )
    return _saida(atualizado, nome, paciente.get("telefone"), _lancamento_do(atualizado, fin))


@router.post("/{data}/{hora}/{agenda_id}/pagamento", response_model=AgendaOut)
def receber(
    data: str,
    hora: str,
    agenda_id: str,
    payload: AgendaPagamento,
    repo: AgendaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
    fin: FinanceiroRepository = Depends(get_financeiro),
) -> dict:
    """Marca o agendamento como pago e lança a **entrada** no Caixa.

    O lançamento leva o `pacienteId` (quando há) mas **nunca `competencia`**: não é
    mensalidade e não pode dar baixa nela. `409` se o agendamento já está pago.
    """
    data = _validar(valida_data, data)
    hora = _validar(valida_hora, hora)
    item = _buscar(repo, data, hora, agenda_id)
    if _lancamento_do(item, fin) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=JA_PAGO)

    nome = item.get("nome") or ""
    if item.get("pacienteId"):
        p = pacientes.get(item["pacienteId"])
        nome = (p or {}).get("nome") or nome
    d = date.fromisoformat(data)
    try:
        lanc_in = LancamentoCreate(
            tipo=TIPO_ENTRADA,
            data=payload.dataPagamento,
            valorCentavos=payload.valorCentavos,
            descricao=f"Agenda — {nome} ({d:%d/%m} às {hora})",
            formaPagamento=payload.formaPagamento,
            pacienteId=item.get("pacienteId"),
        )
    except ValidationError as e:
        msg = (e.errors() or [{}])[0].get("msg", "Requisição inválida")
        raise HTTPException(status_code=400, detail=msg.removeprefix("Value error, "))

    lanc = fin.create(lanc_in.model_dump())
    pagamento = {
        "lancamentoId": lanc["id"],
        "mes": mes_da_data(lanc["data"]),
    }
    antigo = (item.get("pagamento") or {}).get("lancamentoId")
    if not repo.set_pagamento(data, hora, agenda_id, pagamento, antigo):
        # Outro clique pagou primeiro (ou o agendamento foi desmarcado): desfaz o
        # lançamento recém-criado para o Caixa não ficar com dinheiro em dobro.
        fin.soft_delete(pagamento["mes"], lanc["id"])
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=JA_PAGO)

    telefone = (pacientes.get(item["pacienteId"]) or {}).get("telefone") if item.get("pacienteId") else None
    return _saida({**item, "pagamento": pagamento}, nome, telefone, lanc)


@router.delete("/{data}/{hora}/{agenda_id}/pagamento", response_model=AgendaOut)
def desfazer_pagamento(
    data: str,
    hora: str,
    agenda_id: str,
    repo: AgendaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
    fin: FinanceiroRepository = Depends(get_financeiro),
) -> dict:
    """Desfaz o "Pago": cancela o lançamento no Caixa (soft delete, fica na auditoria)
    e tira a referência da marcação."""
    data = _validar(valida_data, data)
    hora = _validar(valida_hora, hora)
    item = _buscar(repo, data, hora, agenda_id)
    pag = item.get("pagamento")
    if pag:
        fin.soft_delete(pag["mes"], pag["lancamentoId"])
        repo.remove_pagamento(data, hora, agenda_id)
    item.pop("pagamento", None)
    if item.get("pacienteId"):
        p = pacientes.get(item["pacienteId"]) or {}
        return _saida(item, p.get("nome") or item.get("nome") or "", p.get("telefone"))
    return _saida(item, item.get("nome") or "")


@router.delete("/{data}/{hora}/{agenda_id}")
def desmarcar(
    data: str,
    hora: str,
    agenda_id: str,
    repo: AgendaRepository = Depends(get_repository),
    fin: FinanceiroRepository = Depends(get_financeiro),
) -> dict:
    """Desmarca (remoção física). `404` se não existe ou é de outra clínica.

    `409` se o agendamento está pago: desfazer o pagamento antes é obrigatório, para o Caixa
    nunca ficar com a entrada de um agendamento que não existe mais.
    """
    data = _validar(valida_data, data)
    hora = _validar(valida_hora, hora)
    item = repo.get(data, hora, agenda_id)
    if item is not None and _lancamento_do(item, fin) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este agendamento está pago. Desfaça o pagamento antes de desmarcar.",
        )
    if not repo.delete(data, hora, agenda_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento não encontrado"
        )
    return {"detail": "Agendamento desmarcado"}
