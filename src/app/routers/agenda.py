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

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_clinic_id
from app.repository import PacienteRepository
from app.repository_agenda import AgendaRepository
from app.schemas_agenda import AgendaCreate, AgendaOut, AgendaVincular, valida_data, valida_hora

router = APIRouter(prefix="/agenda", tags=["agenda"])

# Período máximo de um GET: folga para um mês inteiro de calendário (6 semanas).
PERIODO_MAX_DIAS = 62


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> AgendaRepository:
    return AgendaRepository(clinic_id=clinic_id)


def get_pacientes(clinic_id: str = Depends(get_clinic_id)) -> PacienteRepository:
    return PacienteRepository(clinic_id=clinic_id)


def _validar(fn, valor: str) -> str:
    """Valida query/path params com as regras do schema → 400 com mensagem legível.

    O handler global de `main.py` só alcança erros de validação do **corpo**.
    """
    try:
        return fn(valor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _saida(item: dict, nome: str, telefone=None) -> dict:
    return {
        **item,
        "nome": nome,
        "telefone": telefone if item.get("pacienteId") else item.get("telefone"),
        "novo": not item.get("pacienteId"),
    }


@router.get("", response_model=list[AgendaOut])
def listar_agenda(
    de: str = Query(...),
    ate: str = Query(...),
    repo: AgendaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
) -> list[dict]:
    """Agendamentos de `de` a `ate` (inclusive), ordenados por data → hora → nome."""
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

    saida = []
    for i in itens:
        pid = i.get("pacienteId")
        if pid is None:
            saida.append(_saida(i, i.get("nome") or ""))
        elif pid in ativos:
            p = ativos[pid]
            saida.append(_saida(i, p.get("nome") or i.get("nome") or "", p.get("telefone")))
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
    return _saida(atualizado, nome, paciente.get("telefone"))


@router.delete("/{data}/{hora}/{agenda_id}")
def desmarcar(
    data: str,
    hora: str,
    agenda_id: str,
    repo: AgendaRepository = Depends(get_repository),
) -> dict:
    """Desmarca (remoção física). `404` se não existe ou é de outra clínica."""
    data = _validar(valida_data, data)
    hora = _validar(valida_hora, hora)
    if not repo.delete(data, hora, agenda_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento não encontrado"
        )
    return {"detail": "Agendamento desmarcado"}
