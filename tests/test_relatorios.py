"""Agregações dos relatórios: funções puras, sem DynamoDB (relatorios T4–T8).

Cada bloco cobre os "Done when" da task correspondente em
`.specs/features/relatorios/tasks.md`.
"""
from datetime import datetime, timezone

import pytest

from app import relatorios as r

# ---------------------------------------------------------------------------
# T4 — base + financeiro + extrato
# ---------------------------------------------------------------------------


def test_meses_ate_atravessa_virada_de_ano():
    assert r.meses_ate("2026-02") == [
        "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08",
        "2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
    ]
    assert r.meses_ate("2026-10", 3) == ["2026-08", "2026-09", "2026-10"]


def test_mes_local_usa_horario_de_brasilia():
    # 01:30 UTC do dia 1º = 22:30 do dia 30 em Brasília → mês anterior
    assert r.mes_local("2026-10-01T01:30:00+00:00") == "2026-09"
    assert r.mes_local("2026-10-01T03:00:00+00:00") == "2026-10"
    assert r.mes_local("2026-10-01T01:30:00Z") == "2026-09"
    assert r.mes_local("2027-01-01T02:59:59.123456+00:00") == "2026-12"


def _lanc(tipo, valor, forma=None, data="2026-10-05", desc="x"):
    return {
        "id": f"{tipo}-{valor}-{data}",
        "tipo": tipo,
        "valorCentavos": valor,
        "formaPagamento": forma,
        "data": data,
        "descricao": desc,
        "criadoEm": "2026-10-05T12:00:00+00:00",
    }


def test_resumo_caixa():
    lancs = [_lanc("entrada", 10000), _lanc("entrada", 5000), _lanc("saida", 3000)]
    assert r.resumo_caixa(lancs) == {
        "entradasCentavos": 15000,
        "saidasCentavos": 3000,
        "saldoCentavos": 12000,
    }
    assert r.resumo_caixa([]) == {"entradasCentavos": 0, "saidasCentavos": 0, "saldoCentavos": 0}


def test_receita_por_forma_rotula_legado_e_sem_forma():
    lancs = [
        _lanc("entrada", 6000, "pix"),
        _lanc("entrada", 2000, "PIX"),
        _lanc("entrada", 1000, "cartao"),
        _lanc("entrada", 1000, None),
        _lanc("saida", 99999, "pix"),  # saída não é receita
    ]
    formas = r.receita_por_forma(lancs)
    assert [(f["forma"], f["valorCentavos"]) for f in formas] == [
        ("pix", 8000),
        ("cartao", 1000),
        ("nao_informado", 1000),
    ]
    assert formas[0]["pct"] == 80.0
    assert sum(f["pct"] for f in formas) == pytest.approx(100, abs=0.2)
    assert r.receita_por_forma([]) == []


def test_resumo_mensalidades_conta_por_status():
    mens = {
        "previstoCentavos": 50000,
        "recebidoCentavos": 20000,
        "emAbertoCentavos": 30000,
        "alunos": [{"status": "pago"}, {"status": "aberto"}, {"status": "aberto"}, {"status": "sem_plano"}],
    }
    assert r.resumo_mensalidades(mens) == {
        "previstoCentavos": 50000,
        "recebidoCentavos": 20000,
        "emAbertoCentavos": 30000,
        "porStatus": {"pago": 1, "parcial": 0, "aberto": 2, "isento": 0, "sem_plano": 1},
    }


def test_extrato_mantem_ordem_e_soma_bate_com_saldo():
    lancs = [
        _lanc("entrada", 10000, "pix", "2026-10-01", "Mensalidade Ana"),
        _lanc("saida", 4000, "dinheiro", "2026-10-02", "Material"),
    ]
    ext = r.extrato(lancs)
    assert ext == [
        {"data": "2026-10-01", "descricao": "Mensalidade Ana", "formaPagamento": "pix",
         "tipo": "entrada", "valorCentavos": 10000},
        {"data": "2026-10-02", "descricao": "Material", "formaPagamento": "dinheiro",
         "tipo": "saida", "valorCentavos": 4000},
    ]
    saldo = sum(l["valorCentavos"] * (1 if l["tipo"] == "entrada" else -1) for l in ext)
    assert saldo == r.resumo_caixa(lancs)["saldoCentavos"]


# ---------------------------------------------------------------------------
# T5 — alunos + relação
# ---------------------------------------------------------------------------


def _perfil(pid, nome, criado, removido=None, **extra):
    return {
        "id": pid,
        "nome": nome,
        "ativo": removido is None,
        "criadoEm": criado,
        "atualizadoEm": removido or criado,
        **extra,
    }


PERFIS = [
    _perfil("a", "Ana", "2026-08-10T12:00:00+00:00"),                                   # antiga
    _perfil("b", "Bia", "2026-10-03T12:00:00+00:00"),                                   # nova em out
    _perfil("c", "Caio", "2026-09-01T12:00:00+00:00", "2026-10-20T12:00:00+00:00"),     # sai em out
    _perfil("d", "Duda", "2026-10-05T12:00:00+00:00", "2026-10-25T12:00:00+00:00"),     # entra e sai em out
    _perfil("e", "Edu", "2026-11-01T01:00:00+00:00"),                                   # 31/10 22h BRT → out
]


def test_indicadores_alunos_do_mes():
    ind = r.indicadores_alunos(PERFIS, "2026-10")
    assert ind["novos"] == 3  # Bia, Duda, Edu
    assert ind["saidas"] == 2  # Caio, Duda
    assert ind["ativosFimMes"] == 3  # Ana, Bia, Edu
    assert [n["nome"] for n in ind["novosLista"]] == ["Bia", "Duda", "Edu"]
    assert set(ind["novosLista"][0]) == {"id", "nome", "criadoEm"}


def test_aluno_removido_depois_conta_como_ativo_no_mes_anterior():
    ind = r.indicadores_alunos(PERFIS, "2026-09")
    assert ind["ativosFimMes"] == 2  # Ana e Caio (Caio só sai em outubro)
    assert ind["novos"] == 1 and ind["saidas"] == 0


def test_evolucao_alunos():
    evo = r.evolucao_alunos(PERFIS, ["2026-09", "2026-10"])
    assert evo == [
        {"mes": "2026-09", "ativos": 2, "novos": 1, "saidas": 0},
        {"mes": "2026-10", "ativos": 3, "novos": 3, "saidas": 2},
    ]


def _plano(pid, valor, freq=None, venc=None):
    return {"pacienteId": pid, "valorCentavos": valor, "frequencia": freq, "diaVencimento": venc}


def test_carteira_planos_so_ativos_e_ticket_sem_isentos():
    ativos = [{"id": "a"}, {"id": "b"}, {"id": "x"}, {"id": "y"}]
    planos = [
        _plano("a", 30000, 2),
        _plano("b", 20000, 1),
        _plano("x", 0, 2),  # isento
        _plano("removido", 99999, 3),  # aluno não ativo: fora
        # y sem plano
    ]
    c = r.carteira_planos(planos, ativos)
    assert c["totalMensalCentavos"] == 50000
    assert c["comPlano"] == 2
    assert c["isentos"] == 1
    assert c["semPlano"] == 1
    assert c["ticketMedioCentavos"] == 25000
    assert c["porFrequencia"] == [{"frequencia": 1, "alunos": 1}, {"frequencia": 2, "alunos": 2}]


def test_carteira_vazia():
    c = r.carteira_planos([], [])
    assert c == {
        "totalMensalCentavos": 0, "ticketMedioCentavos": 0, "comPlano": 0,
        "isentos": 0, "semPlano": 0, "porFrequencia": [],
    }


def test_relacao_alunos():
    ativos = [
        {"id": "b", "nome": "bruno", "telefone": "15999", "email": "b@x", "dataNascimento": "1990-01-02"},
        {"id": "a", "nome": "Ana"},
        {"id": "c", "nome": "Carla"},
    ]
    planos = [_plano("a", 30000, 2, 10), _plano("c", 0)]
    matriculas = [
        {"dia": 3, "hora": "07:00", "pacienteId": "a"},
        {"dia": 1, "hora": "18:00", "pacienteId": "a"},
        {"dia": 1, "hora": "07:00", "pacienteId": "a"},
        {"dia": 2, "hora": "07:00", "pacienteId": "fantasma"},
    ]
    rel = r.relacao_alunos(ativos, planos, matriculas)
    assert [a["nome"] for a in rel] == ["Ana", "bruno", "Carla"]
    ana, bruno, carla = rel
    assert ana["plano"] == {"valorCentavos": 30000, "frequencia": 2, "diaVencimento": 10}
    assert ana["isento"] is False
    assert ana["horarios"] == ["Seg 07:00", "Seg 18:00", "Qua 07:00"]
    assert bruno["plano"] is None and bruno["horarios"] == []
    assert bruno["telefone"] == "15999" and bruno["dataNascimento"] == "1990-01-02"
    assert carla["isento"] is True


# ---------------------------------------------------------------------------
# T6 — ocupação
# ---------------------------------------------------------------------------


def _mat(dia, hora, pid):
    return {"dia": dia, "hora": hora, "pacienteId": pid}


def test_ocupacao():
    ativos = [{"id": p, "nome": p.upper()} for p in ("a", "b", "c", "d", "z")]
    mats = [
        _mat(1, "07:00", "a"), _mat(1, "07:00", "b"), _mat(1, "07:00", "c"),
        _mat(3, "18:00", "a"),
        _mat(2, "07:00", "d"),
        _mat(5, "06:00", "orfao"),  # aluno removido: ignorado
    ]
    o = r.ocupacao(mats, ativos)
    assert o["celulas"] == [
        {"dia": 1, "hora": "07:00", "alunos": 3},
        {"dia": 2, "hora": "07:00", "alunos": 1},
        {"dia": 3, "hora": "18:00", "alunos": 1},
    ]
    assert o["matriculas"] == 5
    assert o["alunosDistintos"] == 4
    assert o["mediaPorHorarioOcupado"] == pytest.approx(1.7, abs=0.05)
    assert o["top5"][0] == {"dia": 1, "hora": "07:00", "alunos": 3}
    # desempate por dia e hora
    assert o["top5"][1:] == [{"dia": 2, "hora": "07:00", "alunos": 1}, {"dia": 3, "hora": "18:00", "alunos": 1}]
    assert o["foraDaEscala"] == [{"id": "z", "nome": "Z"}]


def test_ocupacao_grade_vazia():
    o = r.ocupacao([], [{"id": "a", "nome": "Ana"}])
    assert o["celulas"] == [] and o["matriculas"] == 0 and o["alunosDistintos"] == 0
    assert o["mediaPorHorarioOcupado"] == 0 and o["top5"] == []
    assert o["foraDaEscala"] == [{"id": "a", "nome": "Ana"}]


def test_top5_limita_a_cinco():
    mats = [_mat(d, "07:00", f"p{d}") for d in range(1, 8)]
    ativos = [{"id": f"p{d}", "nome": f"P{d}"} for d in range(1, 8)]
    assert len(r.ocupacao(mats, ativos)["top5"]) == 5


# ---------------------------------------------------------------------------
# T7 — atendimento (Pilates + Agenda)
# ---------------------------------------------------------------------------


def _sessao(pid, data, prof_id=None, prof=None, aparelhos=None):
    return {
        "pacienteId": pid,
        "data": data,
        "profissionalId": prof_id,
        "profissional": prof,
        "aparelhos": aparelhos if aparelhos is not None else [],
    }


def _ag(data, pid=None, nome="", prof_id=None, prof_nome=None):
    item = {"data": data, "hora": "07:00", "nome": nome}
    if pid:
        item["pacienteId"] = pid
    if prof_id:
        item["profissionalId"] = prof_id
        item["profissionalNome"] = prof_nome or ""
    return item


def test_meses_agenda_disponiveis_respeita_retencao_de_4_meses():
    agora = int(datetime(2026, 11, 9, tzinfo=timezone.utc).timestamp())
    meses = r.meses_ate("2026-11", 6)  # 2026-06 .. 2026-11
    # 1º/07 + 4m = 1º/11 (já passou: parte de julho pode ter expirado); 1º/08 + 4m = 1º/12 (ok)
    assert r.meses_agenda_disponiveis(meses, agora) == {"2026-08", "2026-09", "2026-10", "2026-11"}


PERFIS_AT = [
    _perfil("a", "Ana", "2026-01-01T12:00:00+00:00"),
    _perfil("b", "Bia", "2026-01-01T12:00:00+00:00", "2026-10-30T12:00:00+00:00"),  # removida, mas teve aula
]
PROFS = {"p1": "Paula (atual)"}


def test_atendimento_fontes_separadas_e_rankings():
    sessoes = [
        _sessao("a", "2026-10-01", "p1", "Paula", [
            {"nome": "Reformer", "treinos": ["Força", "Força", "Mobilidade"]},
            {"nome": "Cadillac", "treinos": ["Força"]},
        ]),
        _sessao("a", "2026-10-08", "p1", "Paula", [{"nome": "Reformer", "treinos": []}]),
        _sessao("b", "2026-10-09", None, None, [{"nome": "Reformer", "treinos": ["Mobilidade"]}]),
        _sessao("b", "2026-10-10", None, "Dra. Ana (texto antigo)", []),
        _sessao("a", "2026-09-15", "p1", "Paula", []),  # mês anterior: só na evolução
    ]
    agenda = [
        _ag("2026-10-02", "a", "Ana", "p1", "Paula"),
        _ag("2026-10-03", None, "Carlos Novo", "p1", "Paula"),
        _ag("2026-10-04", None, "carlos novo"),
        _ag("2026-09-20", "a", "Ana"),
    ]
    meses = ["2026-09", "2026-10"]
    at = r.atendimento(sessoes, agenda, PERFIS_AT, PROFS, "2026-10", meses, {"2026-09", "2026-10"})

    assert at["totalAulas"] == 4
    assert at["totalAgenda"] == 3
    assert at["evolucao"] == [
        {"mes": "2026-09", "aulas": 1, "agenda": 1},
        {"mes": "2026-10", "aulas": 4, "agenda": 3},
    ]
    profs = {p["nome"]: (p["aulas"], p["agenda"]) for p in at["porProfissional"]}
    assert profs == {
        "Paula (atual)": (2, 2),  # nome ao vivo do cadastro
        "Dra. Ana (texto antigo)": (1, 0),
        "Sem profissional": (1, 1),
    }
    assert at["porProfissional"][0]["nome"] == "Paula (atual)"

    alunos = {(a["nome"], a["novo"]): (a["aulas"], a["agenda"]) for a in at["porAluno"]}
    assert alunos == {
        ("Ana", False): (2, 1),
        ("Bia", False): (2, 0),  # removida continua aparecendo pelo nome do perfil
        ("Carlos Novo", True): (0, 2),  # marcações de aluno novo agrupadas pelo nome
    }
    assert at["aparelhos"] == [{"nome": "Reformer", "aulas": 3}, {"nome": "Cadillac", "aulas": 1}]
    # treino conta 1 por aula em que aparece (Força em 2 aparelhos da mesma aula = 1)
    assert at["treinos"] == [{"nome": "Mobilidade", "aulas": 2}, {"nome": "Força", "aulas": 1}]


def test_atendimento_agenda_expirada_vira_none_nao_zero():
    sessoes = [_sessao("a", "2026-05-10", "p1", "Paula", [])]
    agenda = []
    at = r.atendimento(sessoes, agenda, PERFIS_AT, PROFS, "2026-05", ["2026-04", "2026-05"], set())
    assert at["totalAulas"] == 1
    assert at["totalAgenda"] is None
    assert at["evolucao"] == [
        {"mes": "2026-04", "aulas": 0, "agenda": None},
        {"mes": "2026-05", "aulas": 1, "agenda": None},
    ]
    assert at["porProfissional"] == [{"profissionalId": "p1", "nome": "Paula (atual)", "aulas": 1, "agenda": None}]
    assert at["porAluno"][0]["agenda"] is None


def test_atendimento_vazio():
    at = r.atendimento([], [], [], {}, "2026-10", ["2026-10"], {"2026-10"})
    assert at["totalAulas"] == 0 and at["totalAgenda"] == 0
    assert at["porProfissional"] == [] and at["porAluno"] == []
    assert at["aparelhos"] == [] and at["treinos"] == []


# ---------------------------------------------------------------------------
# T8 — semana
# ---------------------------------------------------------------------------


def test_segunda_da_semana():
    assert r.segunda_da_semana("2026-11-09") == "2026-11-09"  # segunda
    assert r.segunda_da_semana("2026-11-15") == "2026-11-09"  # domingo
    assert r.segunda_da_semana("2027-01-01") == "2026-12-28"  # vira o ano


def test_semana():
    sessoes = [
        _sessao("a", "2026-12-28"),
        _sessao("a", "2026-12-28"),
        _sessao("b", "2027-01-01"),
    ]
    agenda = [_ag("2026-12-30", "a", "Ana"), _ag("2027-01-03", None, "Novo Fulano")]
    s = r.semana(sessoes, agenda, PERFIS_AT, "2026-12-28", True)
    assert s["inicio"] == "2026-12-28" and s["fim"] == "2027-01-03"
    assert s["agendaDisponivel"] is True
    assert s["distintos"] == 3 and s["totalAulas"] == 3 and s["totalAgenda"] == 2
    assert [a["nome"] for a in s["alunos"]] == ["Ana", "Bia", "Novo Fulano"]
    ana = s["alunos"][0]
    assert ana["dias"]["1"] == {"aula": 2, "agenda": 0}
    assert ana["dias"]["3"] == {"aula": 0, "agenda": 1}
    assert ana["total"] == 3
    assert set(ana["dias"]) == {"1", "2", "3", "4", "5", "6", "7"}
    assert s["alunos"][2]["novo"] is True and s["alunos"][2]["dias"]["7"]["agenda"] == 1


def test_semana_com_agenda_expirada_ignora_agenda():
    sessoes = [_sessao("a", "2026-05-04")]
    agenda = [_ag("2026-05-05", "b", "Bia")]  # não deveria nem vir, mas se vier, não conta
    s = r.semana(sessoes, agenda, PERFIS_AT, "2026-05-04", False)
    assert s["agendaDisponivel"] is False
    assert s["totalAgenda"] == 0
    assert [a["nome"] for a in s["alunos"]] == ["Ana"]
