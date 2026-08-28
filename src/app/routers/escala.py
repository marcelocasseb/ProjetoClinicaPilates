"""Endpoints da Escala Semanal — grade fixa de horários da clínica (feature escala).

Rotas de **nível clínica** (`/escala`, como `/aparelhos`), multi-tenant (AD-007): o
`clinicId` vem de `get_clinic_id` (deps.py), nunca do corpo da requisição.

A matrícula é o par aluno + dia (1=segunda … 7=domingo) + horário `HH:MM`. Ela guarda um
snapshot do nome, mas a **exibição usa o nome ao vivo** do cadastro: o `GET` cruza a
grade com `PacienteRepository.list_ativos()`, o que de quebra **descarta matrículas
órfãs** (aluno removido do cadastro depois de matriculado). Assim a grade se auto-limpa,
sem cascata na remoção do paciente (ESC-09).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.deps import get_clinic_id
from app.repository import PacienteRepository
from app.repository_escala import EscalaRepository
from app.schemas_escala import EscalaCreate, EscalaOut

router = APIRouter(prefix="/escala", tags=["escala"])


def get_repository(clinic_id: str = Depends(get_clinic_id)) -> EscalaRepository:
    return EscalaRepository(clinic_id=clinic_id)


def get_pacientes(clinic_id: str = Depends(get_clinic_id)) -> PacienteRepository:
    return PacienteRepository(clinic_id=clinic_id)


def _validar_chave(dia: str, hora: str, paciente_id: str) -> EscalaCreate:
    """Valida os path params do DELETE com o mesmo schema do POST.

    O handler global de `main.py` só alcança erros de validação do **corpo**; aqui a
    `ValidationError` é convertida à mão para o mesmo 400 com mensagem legível.
    """
    try:
        return EscalaCreate(dia=dia, hora=hora, pacienteId=paciente_id)
    except ValidationError as e:
        erros = e.errors()
        msg = erros[0].get("msg", "Requisição inválida") if erros else "Requisição inválida"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg.removeprefix("Value error, "))


@router.get("", response_model=list[EscalaOut])
def listar_escala(
    repo: EscalaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
) -> list[dict]:
    """Grade da semana da clínica (ESC-01), ordenada por dia → hora → nome.

    Matrículas de alunos removidos do cadastro são omitidas; o nome exibido é o do
    cadastro (o snapshot da matrícula é só fallback).
    """
    ativos = {p["id"]: (p.get("nome") or "") for p in pacientes.list_ativos()}
    grade = [
        {
            "dia": m["dia"],
            "hora": m["hora"],
            "pacienteId": m["pacienteId"],
            "nome": ativos[m["pacienteId"]] or m.get("pacienteNome") or "",
            "criadoEm": m.get("criadoEm"),
        }
        for m in repo.list_all()
        if m["pacienteId"] in ativos
    ]
    grade.sort(key=lambda m: (m["dia"], m["hora"], m["nome"].lower()))
    return grade


@router.post("", response_model=EscalaOut, status_code=status.HTTP_201_CREATED)
def matricular(
    payload: EscalaCreate,
    repo: EscalaRepository = Depends(get_repository),
    pacientes: PacienteRepository = Depends(get_pacientes),
) -> dict:
    """Coloca um aluno num dia+horário da grade (ESC-03).

    `404` se o aluno não existe/foi removido/é de outra clínica; `409` se ele já está
    neste horário (a chave do item é o próprio par aluno+dia+hora).
    """
    paciente = pacientes.get(payload.pacienteId)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    nome = paciente.get("nome") or ""
    criado = repo.create(payload.dia, payload.hora, payload.pacienteId, nome)
    if criado is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este aluno já está neste horário"
        )
    return {**criado, "nome": nome}


@router.delete("/{dia}/{hora}/{paciente_id}")
def desmatricular(
    dia: str,
    hora: str,
    paciente_id: str,
    repo: EscalaRepository = Depends(get_repository),
) -> dict:
    """Tira o aluno do horário (ESC-05) — remoção física, a escala é estado atual.

    `404` se a matrícula não existe ou é de outra clínica.
    """
    chave = _validar_chave(dia, hora, paciente_id)
    if not repo.delete(chave.dia, chave.hora, chave.pacienteId):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada"
        )
    return {"detail": "Aluno removido do horário"}
