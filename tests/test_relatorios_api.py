"""Endpoints `GET /relatorios/*` (relatorios T10 / REL-01..22).

Cobre: só admin (403 para membro), isolamento entre clínicas, números iguais aos das
telas Caixa e Mensalidades, Agenda no Atendimento e na Semana, clínica vazia e
validação de mês/semana. As regras de conta em si estão em `test_relatorios.py`.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import relatorios as r
from app.deps import get_claims, get_clinic_id
from app.main import app
from app.repository import PacienteRepository
from app.repository_agenda import AgendaRepository
from app.repository_escala import EscalaRepository
from app.repository_financeiro import FinanceiroRepository
from app.repository_plano import PlanoRepository
from app.repository_profissional import ProfissionalRepository
from app.repository_sessao import SessaoRepository

client = TestClient(app)

ADMIN = {"custom:clinicId": "clinica-a", "custom:role": "admin"}
ADMIN_B = {"custom:clinicId": "clinica-b", "custom:role": "admin"}
MEMBRO = {"custom:clinicId": "clinica-a", "custom:role": "membro"}

ROTAS = [
    "/relatorios/financeiro",
    "/relatorios/alunos",
    "/relatorios/relacao-alunos",
    "/relatorios/ocupacao",
    "/relatorios/atendimento",
    "/relatorios/semana",
]

HOJE = r.hoje_local()
MES = HOJE.strftime("%Y-%m")  # mês corrente: a Agenda dele está sempre disponível
DIA = f"{MES}-01"


@pytest.fixture
def as_user():
    def _set(claims):
        app.dependency_overrides.pop(get_clinic_id, None)
        app.dependency_overrides[get_claims] = lambda: claims

    yield _set
    app.dependency_overrides.pop(get_claims, None)


def _povoar(clinic):
    """Uma clínica com 2 alunos, plano, grade, caixa, aula e marcação no mês corrente."""
    pac = PacienteRepository(clinic)
    ana = pac.create({"nome": f"Ana {clinic}", "telefone": "15999990000"})
    bia = pac.create({"nome": f"Bia {clinic}"})
    PlanoRepository(clinic).upsert(ana["id"], {"valorCentavos": 30000, "frequencia": 2, "diaVencimento": 10})
    EscalaRepository(clinic).create(1, "07:00", ana["id"], ana["nome"])
    fin = FinanceiroRepository(clinic)
    fin.create({"tipo": "entrada", "data": DIA, "valorCentavos": 20000, "descricao": "Mensalidade",
                "formaPagamento": "pix", "pacienteId": ana["id"], "competencia": MES})
    fin.create({"tipo": "saida", "data": DIA, "valorCentavos": 5000, "descricao": "Luz",
                "formaPagamento": "dinheiro"})
    prof = ProfissionalRepository(clinic).create({"nome": "Paula"})
    SessaoRepository(clinic, ana["id"]).create(
        {"data": DIA, "profissionalId": prof["id"], "profissional": "Paula",
         "aparelhos": [{"nome": "Reformer", "treinos": ["Força"]}]}
    )
    AgendaRepository(clinic).create(DIA, "08:00", bia["id"], bia["nome"], None, prof["id"], "Paula")
    return {"ana": ana, "bia": bia, "prof": prof}


# --- acesso -----------------------------------------------------------------


@pytest.mark.parametrize("rota", ROTAS)
def test_membro_recebe_403(dynamo_table, as_user, rota):
    as_user(MEMBRO)
    assert client.get(rota).status_code == 403


@pytest.mark.parametrize("rota", ROTAS)
def test_clinica_vazia_devolve_zeros(dynamo_table, as_user, rota):
    as_user(ADMIN)
    resp = client.get(rota)
    assert resp.status_code == 200, resp.text


def test_isolamento_entre_clinicas(dynamo_table, as_user):
    _povoar("clinica-a")
    as_user(ADMIN_B)

    fin = client.get("/relatorios/financeiro").json()
    assert fin["caixa"]["entradasCentavos"] == 0 and fin["extrato"] == []
    alunos = client.get("/relatorios/alunos").json()
    assert alunos["ativosFimMes"] == 0
    assert client.get("/relatorios/relacao-alunos").json()["alunos"] == []
    assert client.get("/relatorios/ocupacao").json()["matriculas"] == 0
    at = client.get("/relatorios/atendimento").json()
    assert at["totalAulas"] == 0 and at["totalAgenda"] == 0 and at["porAluno"] == []
    assert client.get("/relatorios/semana").json()["alunos"] == []


# --- conteúdo -----------------------------------------------------------------


def test_financeiro_bate_com_caixa_e_mensalidades(dynamo_table, as_user):
    _povoar("clinica-a")
    as_user(ADMIN)

    rel = client.get(f"/relatorios/financeiro?mes={MES}").json()
    caixa = client.get(f"/financeiro/lancamentos?mes={MES}").json()
    mens = client.get(f"/financeiro/mensalidades?mes={MES}").json()

    assert rel["caixa"] == {k: caixa[k] for k in ("entradasCentavos", "saidasCentavos", "saldoCentavos")}
    assert rel["mensalidades"]["previstoCentavos"] == mens["previstoCentavos"]
    assert rel["mensalidades"]["recebidoCentavos"] == mens["recebidoCentavos"]
    assert rel["mensalidades"]["emAbertoCentavos"] == mens["emAbertoCentavos"]
    assert rel["mensalidades"]["porStatus"]["parcial"] == 1
    assert rel["mensalidades"]["porStatus"]["sem_plano"] == 1
    assert len(rel["evolucao"]) == 12 and rel["evolucao"][-1]["mes"] == MES
    assert rel["evolucao"][-1]["saldoCentavos"] == 15000
    assert [l["descricao"] for l in rel["extrato"]] == [l["descricao"] for l in caixa["lancamentos"]]
    assert rel["porForma"] == [{"forma": "pix", "valorCentavos": 20000, "pct": 100.0}]


def test_alunos_e_relacao(dynamo_table, as_user):
    _povoar("clinica-a")
    as_user(ADMIN)

    alunos = client.get(f"/relatorios/alunos?mes={MES}").json()
    assert alunos["novos"] == 2 and alunos["ativosFimMes"] == 2
    assert alunos["carteira"]["totalMensalCentavos"] == 30000
    assert alunos["carteira"]["semPlano"] == 1

    rel = client.get("/relatorios/relacao-alunos").json()
    assert rel["total"] == 2
    ana = rel["alunos"][0]
    assert ana["nome"] == "Ana clinica-a"
    assert ana["horarios"] == ["Seg 07:00"]
    assert ana["plano"]["valorCentavos"] == 30000


def test_ocupacao(dynamo_table, as_user):
    _povoar("clinica-a")
    as_user(ADMIN)
    o = client.get("/relatorios/ocupacao").json()
    assert o["celulas"] == [{"dia": 1, "hora": "07:00", "alunos": 1}]
    assert [a["nome"] for a in o["foraDaEscala"]] == ["Bia clinica-a"]


def test_atendimento_traz_pilates_e_agenda_separados(dynamo_table, as_user):
    dados = _povoar("clinica-a")
    as_user(ADMIN)

    at = client.get(f"/relatorios/atendimento?mes={MES}").json()
    assert at["totalAulas"] == 1 and at["totalAgenda"] == 1
    assert at["agendaRetencaoMeses"] == 4
    assert at["porProfissional"] == [
        {"profissionalId": dados["prof"]["id"], "nome": "Paula", "aulas": 1, "agenda": 1}
    ]
    nomes = {a["nome"]: (a["aulas"], a["agenda"]) for a in at["porAluno"]}
    assert nomes == {"Ana clinica-a": (1, 0), "Bia clinica-a": (0, 1)}
    assert at["aparelhos"] == [{"nome": "Reformer", "aulas": 1}]
    assert len(at["evolucao"]) == 12


def test_semana(dynamo_table, as_user):
    _povoar("clinica-a")
    as_user(ADMIN)
    segunda = r.segunda_da_semana(DIA)

    s = client.get(f"/relatorios/semana?inicio={segunda}").json()
    assert s["inicio"] == segunda
    assert s["agendaDisponivel"] is True
    assert s["totalAulas"] == 1 and s["totalAgenda"] == 1
    assert [a["nome"] for a in s["alunos"]] == ["Ana clinica-a", "Bia clinica-a"]


def test_padroes_sem_parametro_usam_hoje(dynamo_table, as_user):
    as_user(ADMIN)
    assert client.get("/relatorios/financeiro").json()["mes"] == MES
    assert client.get("/relatorios/semana").json()["inicio"] == r.segunda_da_semana(HOJE.isoformat())


# --- validação ----------------------------------------------------------------


@pytest.mark.parametrize("rota", ["/relatorios/financeiro", "/relatorios/alunos", "/relatorios/atendimento"])
@pytest.mark.parametrize("mes", ["2026-13", "abc", "2026-1"])
def test_mes_invalido_400(dynamo_table, as_user, rota, mes):
    as_user(ADMIN)
    assert client.get(f"{rota}?mes={mes}").status_code == 400


@pytest.mark.parametrize("rota", ["/relatorios/financeiro", "/relatorios/alunos", "/relatorios/atendimento"])
def test_mes_futuro_400(dynamo_table, as_user, rota):
    as_user(ADMIN)
    futuro = r.meses_ate(MES, 1)[0]
    ano, m = int(futuro[:4]), int(futuro[5:])
    futuro = f"{ano + (m == 12):04d}-{m % 12 + 1:02d}"
    assert client.get(f"{rota}?mes={futuro}").status_code == 400


def test_semana_invalida_400(dynamo_table, as_user):
    as_user(ADMIN)
    segunda = r.segunda_da_semana(HOJE.isoformat())
    terca = (HOJE - timedelta(days=HOJE.weekday()) + timedelta(days=1)).isoformat()
    proxima = (HOJE - timedelta(days=HOJE.weekday()) + timedelta(days=7)).isoformat()
    assert client.get(f"/relatorios/semana?inicio={segunda}").status_code == 200
    assert client.get(f"/relatorios/semana?inicio={terca}").status_code == 400
    assert client.get(f"/relatorios/semana?inicio={proxima}").status_code == 400
    assert client.get("/relatorios/semana?inicio=2026-02-30").status_code == 400
