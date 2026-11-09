"""Conta das mensalidades como função pura (relatorios T1 / REL-06).

A mesma função atende a tela Mensalidades e o relatório Financeiro, então os dois números
não têm como divergir. Os testes de endpoint (`test_mensalidades.py`) continuam valendo
para o comportamento HTTP; aqui fica a regra de negócio isolada, sem DynamoDB.
"""
from app.mensalidades import calcular_mensalidades


def _aluno(pid, nome):
    return {"id": pid, "nome": nome}


def _plano(pid, valor, freq=None, venc=None):
    return {"pacienteId": pid, "valorCentavos": valor, "frequencia": freq, "diaVencimento": venc}


def _pag(pid, valor, tipo="entrada"):
    return {"pacienteId": pid, "valorCentavos": valor, "tipo": tipo}


def test_status_de_cada_situacao_e_totais():
    alunos = [
        _aluno("a", "Ana"),
        _aluno("b", "bruno"),
        _aluno("c", "Carla"),
        _aluno("d", "Duda"),
        _aluno("e", "Edu"),
    ]
    planos = [
        _plano("a", 30000, freq=2, venc=10),  # pago
        _plano("b", 30000),  # parcial
        _plano("c", 25000),  # aberto
        _plano("d", 0),  # isento
        # "e" sem plano
    ]
    pagamentos = [
        _pag("a", 30000),
        _pag("b", 10000),
        _pag("c", 5000, tipo="saida"),  # saída nunca conta como pagamento
    ]
    escala = [{"pacienteId": "a"}, {"pacienteId": "a"}, {"pacienteId": "a"}]

    r = calcular_mensalidades("2026-10", alunos, planos, pagamentos, escala)

    assert r["mes"] == "2026-10"
    assert r["previstoCentavos"] == 85000
    assert r["recebidoCentavos"] == 40000
    assert r["emAbertoCentavos"] == 20000 + 25000
    status = {l["pacienteId"]: l["status"] for l in r["alunos"]}
    assert status == {"a": "pago", "b": "parcial", "c": "aberto", "d": "isento", "e": "sem_plano"}
    # ordem alfabética sem diferenciar maiúsculas
    assert [l["nome"] for l in r["alunos"]] == ["Ana", "bruno", "Carla", "Duda", "Edu"]
    ana = r["alunos"][0]
    assert ana["frequencia"] == 2 and ana["frequenciaEscala"] == 3
    assert ana["divergenciaEscala"] is True
    assert ana["diaVencimento"] == 10


def test_pagamento_a_mais_nao_esconde_divida_de_outro():
    alunos = [_aluno("a", "A"), _aluno("b", "B")]
    planos = [_plano("a", 10000), _plano("b", 10000)]
    pagamentos = [_pag("a", 30000)]

    r = calcular_mensalidades("2026-10", alunos, planos, pagamentos, [])

    assert r["emAbertoCentavos"] == 10000


def test_sem_alunos_devolve_zeros():
    r = calcular_mensalidades("2026-10", [], [], [], [])
    assert r == {
        "mes": "2026-10",
        "previstoCentavos": 0,
        "recebidoCentavos": 0,
        "emAbertoCentavos": 0,
        "alunos": [],
    }
