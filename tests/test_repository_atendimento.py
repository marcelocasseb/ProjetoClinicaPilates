"""Leitura das aulas de vários alunos num período (relatorios T3 / REL-13, REL-19, REL-22).

As aulas ficam sob a PK de cada aluno; o relatório lê aluno a aluno, em paralelo.
Usa a fixture `dynamo_table` (moto) de conftest.py.
"""
import boto3
import pytest

from app.repository import PacienteRepository
from app.repository_atendimento import list_sessoes_periodo
from app.repository_avaliacao import AvaliacaoRepository
from app.repository_sessao import SessaoRepository

CLINICA_A = "clinica-a"
CLINICA_B = "clinica-b"


def _aula(clinic, paciente_id, data, profissional="Ana"):
    return SessaoRepository(clinic, paciente_id).create(
        {
            "data": data,
            "profissional": profissional,
            "aparelhos": [{"aparelhoId": "x", "nome": "Reformer", "treinos": ["Força"]}],
        }
    )


@pytest.fixture
def alunos(dynamo_table):
    repo = PacienteRepository(CLINICA_A)
    return [repo.create({"nome": n})["id"] for n in ("Ana", "Bia", "Caio")]


def test_traz_aulas_do_periodo_de_todos_os_alunos(alunos):
    a, b, c = alunos
    _aula(CLINICA_A, a, "2026-10-01")
    _aula(CLINICA_A, a, "2026-10-31")
    _aula(CLINICA_A, b, "2026-10-15")
    _aula(CLINICA_A, c, "2026-09-30")  # fora (antes)
    _aula(CLINICA_A, c, "2026-11-01")  # fora (depois)

    sessoes = list_sessoes_periodo(CLINICA_A, alunos, "2026-10-01", "2026-10-31")

    assert sorted((s["pacienteId"], s["data"]) for s in sessoes) == sorted(
        [(a, "2026-10-01"), (a, "2026-10-31"), (b, "2026-10-15")]
    )
    assert sessoes[0]["aparelhos"][0]["nome"] == "Reformer"
    assert not any(k in sessoes[0] for k in ("PK", "SK"))


def test_ignora_aula_removida(alunos):
    a = alunos[0]
    viva = _aula(CLINICA_A, a, "2026-10-05")
    morta = _aula(CLINICA_A, a, "2026-10-06")
    SessaoRepository(CLINICA_A, a).soft_delete(morta["id"])

    sessoes = list_sessoes_periodo(CLINICA_A, [a], "2026-10-01", "2026-10-31")

    assert [s["id"] for s in sessoes] == [viva["id"]]


def test_ignora_avaliacoes_e_perfil_sob_a_mesma_pk(alunos):
    a = alunos[0]
    AvaliacaoRepository(CLINICA_A, a).create({"data": "2026-10-10"})

    assert list_sessoes_periodo(CLINICA_A, [a], "2026-10-01", "2026-10-31") == []


def test_isolamento_ids_de_outra_clinica_nao_retornam(alunos):
    repo_b = PacienteRepository(CLINICA_B)
    aluno_b = repo_b.create({"nome": "Da B"})["id"]
    _aula(CLINICA_B, aluno_b, "2026-10-10")

    # Mesmo pedindo o id do aluno da B, a clínica A não lê a aula dele.
    assert list_sessoes_periodo(CLINICA_A, [aluno_b], "2026-10-01", "2026-10-31") == []
    assert len(list_sessoes_periodo(CLINICA_B, [aluno_b], "2026-10-01", "2026-10-31")) == 1


def test_lista_vazia_nao_consulta_o_banco(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("não deveria criar client")

    monkeypatch.setattr(boto3, "client", explode)
    assert list_sessoes_periodo(CLINICA_A, [], "2026-10-01", "2026-10-31") == []


def test_muitos_alunos_em_paralelo(alunos, dynamo_table):
    repo = PacienteRepository(CLINICA_A)
    ids = [repo.create({"nome": f"Aluno {i}"})["id"] for i in range(40)]
    for pid in ids:
        _aula(CLINICA_A, pid, "2026-10-20")

    sessoes = list_sessoes_periodo(CLINICA_A, ids, "2026-10-01", "2026-10-31")

    assert sorted(s["pacienteId"] for s in sessoes) == sorted(ids)
