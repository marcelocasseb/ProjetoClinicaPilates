"""Testes da tela de Mensalidades: previsto × recebido × em aberto (fluxo-caixa F2)."""
import pytest
from fastapi.testclient import TestClient

from app.deps import get_claims, get_clinic_id
from app.main import app

client = TestClient(app)

ADMIN = {"custom:clinicId": "clinica-a", "custom:role": "admin"}
ADMIN_B = {"custom:clinicId": "clinica-b", "custom:role": "admin"}
MEMBRO = {"custom:clinicId": "clinica-a", "custom:role": "membro"}

MES = "2026-10"


@pytest.fixture
def as_user():
    def _set(claims):
        app.dependency_overrides.pop(get_clinic_id, None)
        app.dependency_overrides[get_claims] = lambda: claims

    yield _set
    app.dependency_overrides.pop(get_claims, None)


def _aluno(nome):
    return client.post("/pacientes", json={"nome": nome}).json()["id"]


def _plano(pid, valor, **extra):
    return client.put(f"/financeiro/planos/{pid}", json={"valorCentavos": valor, **extra})


def _pagar(pid, valor, competencia=MES, data=f"{MES}-05"):
    return client.post(
        "/financeiro/lancamentos",
        json={
            "tipo": "entrada",
            "data": data,
            "valorCentavos": valor,
            "descricao": "Mensalidade",
            "pacienteId": pid,
            "competencia": competencia,
        },
    )


def _mensalidades(mes=MES):
    return client.get(f"/financeiro/mensalidades?mes={mes}").json()


def _por_nome(corpo, nome):
    return next(a for a in corpo["alunos"] if a["nome"] == nome)


# --- lista base -----------------------------------------------------------


def test_clinica_sem_aluno(dynamo_table, as_user):
    as_user(ADMIN)
    corpo = _mensalidades()
    assert corpo["alunos"] == []
    assert corpo["previstoCentavos"] == 0
    assert corpo["recebidoCentavos"] == 0
    assert corpo["emAbertoCentavos"] == 0


def test_lista_vem_do_cadastro_mesmo_sem_escala_e_sem_plano(dynamo_table, as_user):
    """O ponto central: funciona 100% numa clínica que não usa a Escala."""
    as_user(ADMIN)
    _aluno("Marina Costa")
    _aluno("Ana Lucia")

    corpo = _mensalidades()
    assert [a["nome"] for a in corpo["alunos"]] == ["Ana Lucia", "Marina Costa"]
    assert all(a["status"] == "sem_plano" for a in corpo["alunos"])
    assert all(a["temPlano"] is False for a in corpo["alunos"])
    assert corpo["previstoCentavos"] == 0


def test_alunos_ordenados_por_nome(dynamo_table, as_user):
    as_user(ADMIN)
    for nome in ("Zeca", "ana", "Bruno"):
        _aluno(nome)
    assert [a["nome"] for a in _mensalidades()["alunos"]] == ["ana", "Bruno", "Zeca"]


def test_aluno_removido_some_da_lista(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    client.delete(f"/pacientes/{pid}")

    corpo = _mensalidades()
    assert corpo["alunos"] == []
    assert corpo["previstoCentavos"] == 0


# --- status por aluno -----------------------------------------------------


def test_status_aberto(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000, diaVencimento=5)

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["status"] == "aberto"
    assert linha["valorCentavos"] == 26000
    assert linha["pagoCentavos"] == 0
    assert linha["emAbertoCentavos"] == 26000
    assert linha["diaVencimento"] == 5


def test_status_pago(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    _pagar(pid, 26000)

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["status"] == "pago"
    assert linha["pagoCentavos"] == 26000
    assert linha["emAbertoCentavos"] == 0


def test_status_parcial(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    _pagar(pid, 13000)

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["status"] == "parcial"
    assert linha["emAbertoCentavos"] == 13000


def test_duas_parcelas_somam_e_fecham(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    _pagar(pid, 13000)
    _pagar(pid, 13000)

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["pagoCentavos"] == 26000
    assert linha["status"] == "pago"


def test_status_isento_difere_de_sem_plano(dynamo_table, as_user):
    """Bolsista (plano com valor 0) é resolvido; sem plano é trabalho pendente."""
    as_user(ADMIN)
    bolsista = _aluno("Carlos Bolsista")
    _plano(bolsista, 0)
    _aluno("Ana Sem Plano")

    corpo = _mensalidades()
    assert _por_nome(corpo, "Carlos Bolsista")["status"] == "isento"
    assert _por_nome(corpo, "Carlos Bolsista")["temPlano"] is True
    assert _por_nome(corpo, "Ana Sem Plano")["status"] == "sem_plano"
    assert corpo["previstoCentavos"] == 0


def test_pagamento_a_maior_nao_fica_negativo(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    _pagar(pid, 30000)

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["status"] == "pago"
    assert linha["emAbertoCentavos"] == 0


# --- totais ---------------------------------------------------------------


def test_totais_previsto_recebido_em_aberto(dynamo_table, as_user):
    as_user(ADMIN)
    a = _aluno("Aluno A")
    b = _aluno("Aluno B")
    c = _aluno("Aluno C")
    _plano(a, 26000)
    _plano(b, 34000)
    _plano(c, 16000)
    _pagar(a, 26000)
    _pagar(b, 10000)

    corpo = _mensalidades()
    assert corpo["previstoCentavos"] == 76000
    assert corpo["recebidoCentavos"] == 36000
    assert corpo["emAbertoCentavos"] == 40000  # 24.000 do B + 16.000 do C


def test_em_aberto_e_somado_por_aluno(dynamo_table, as_user):
    """Quem pagou a mais não pode mascarar a dívida de outro no total da clínica."""
    as_user(ADMIN)
    a = _aluno("Aluno A")
    b = _aluno("Aluno B")
    _plano(a, 10000)
    _plano(b, 10000)
    _pagar(a, 30000)  # pagou 3 meses adiantado

    corpo = _mensalidades()
    assert corpo["emAbertoCentavos"] == 10000, "o B continua devendo"


def test_pagamento_de_outra_competencia_nao_conta(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    _pagar(pid, 26000, competencia="2026-09", data="2026-09-05")

    assert _por_nome(_mensalidades(MES), "Marina Costa")["status"] == "aberto"
    assert _por_nome(_mensalidades("2026-09"), "Marina Costa")["status"] == "pago"


def test_mensalidade_atrasada_paga_no_mes_seguinte_conta_na_competencia(dynamo_table, as_user):
    """O caso que motivou indexar o GSI1 por competência, e não por aluno."""
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    # Competência de setembro, dinheiro que entrou em 3 de OUTUBRO.
    _pagar(pid, 26000, competencia="2026-09", data="2026-10-03")

    assert _por_nome(_mensalidades("2026-09"), "Marina Costa")["status"] == "pago"
    # E o caixa continua contando o dinheiro no mês em que ele andou.
    caixa = client.get(f"/financeiro/lancamentos?mes={MES}").json()
    assert caixa["entradasCentavos"] == 26000


def test_saida_com_competencia_nao_conta_como_pagamento(dynamo_table, as_user):
    """Estorno/devolução ao aluno é saída — não pode virar 'mensalidade paga'."""
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    client.post(
        "/financeiro/lancamentos",
        json={
            "tipo": "saida",
            "data": f"{MES}-06",
            "valorCentavos": 26000,
            "descricao": "Devolucao",
            "pacienteId": pid,
            "competencia": MES,
        },
    )
    assert _por_nome(_mensalidades(), "Marina Costa")["status"] == "aberto"


def test_pagamento_cancelado_volta_a_ficar_em_aberto(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    lanc_id = _pagar(pid, 26000).json()["id"]
    client.delete(f"/financeiro/lancamentos/{MES}/{lanc_id}")

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["status"] == "aberto"
    assert linha["pagoCentavos"] == 0


# --- divergência com a escala --------------------------------------------


def test_sem_escala_nao_ha_divergencia(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000, frequencia=2)

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["frequenciaEscala"] is None
    assert linha["divergenciaEscala"] is False


def test_divergencia_quando_grade_diz_outra_coisa(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000, frequencia=2)
    for dia in (1, 3, 5):  # 3 horários na grade, plano diz 2
        client.post("/escala", json={"dia": dia, "hora": "07:00", "pacienteId": pid})

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["frequenciaEscala"] == 3
    assert linha["divergenciaEscala"] is True


def test_sem_divergencia_quando_bate(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000, frequencia=2)
    for dia in (1, 3):
        client.post("/escala", json={"dia": dia, "hora": "07:00", "pacienteId": pid})

    linha = _por_nome(_mensalidades(), "Marina Costa")
    assert linha["frequenciaEscala"] == 2
    assert linha["divergenciaEscala"] is False


# --- planos: escrita ------------------------------------------------------


def test_definir_plano_201_e_reflete_na_tela(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    resp = _plano(pid, 26000, diaVencimento=5, frequencia=2)

    assert resp.status_code == 200
    assert resp.json()["valorCentavos"] == 26000
    assert _por_nome(_mensalidades(), "Marina Costa")["valorCentavos"] == 26000


def test_plano_de_aluno_inexistente_404(dynamo_table, as_user):
    as_user(ADMIN)
    assert _plano("nao-existe", 26000).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"valorCentavos": -1},
        {"valorCentavos": 260.5},
        {"valorCentavos": "abc"},
        {"valorCentavos": 26000, "diaVencimento": 0},
        {"valorCentavos": 26000, "diaVencimento": 32},
        {"valorCentavos": 26000, "frequencia": 8},
        {"valorCentavos": 26000, "frequencia": 0},
        {"valorCentavos": 26000, "observacao": "x" * 201},
    ],
)
def test_plano_invalido_400(dynamo_table, as_user, payload):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    assert client.put(f"/financeiro/planos/{pid}", json=payload).status_code == 400


def test_remover_plano(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)

    assert client.delete(f"/financeiro/planos/{pid}").status_code == 200
    assert client.delete(f"/financeiro/planos/{pid}").status_code == 404
    assert _por_nome(_mensalidades(), "Marina Costa")["status"] == "sem_plano"


# --- tabela de preços -----------------------------------------------------


def test_config_padrao_nunca_404(dynamo_table, as_user):
    as_user(ADMIN)
    resp = client.get("/financeiro/config")
    assert resp.status_code == 200
    assert resp.json() == {"tabelaPrecos": [], "aulaAvulsaCentavos": 0, "reposicaoCentavos": 0}


def test_salvar_e_ler_config(dynamo_table, as_user):
    as_user(ADMIN)
    resp = client.put(
        "/financeiro/config",
        json={
            "tabelaPrecos": [
                {"frequencia": 1, "valorCentavos": 16000},
                {"frequencia": 2, "valorCentavos": 26000},
            ],
            "aulaAvulsaCentavos": 5000,
            "reposicaoCentavos": 0,
        },
    )
    assert resp.status_code == 200
    lido = client.get("/financeiro/config").json()
    assert lido["aulaAvulsaCentavos"] == 5000
    assert lido["tabelaPrecos"][1] == {"frequencia": 2, "valorCentavos": 26000}


@pytest.mark.parametrize(
    "payload",
    [
        {"tabelaPrecos": [{"frequencia": 9, "valorCentavos": 100}]},
        {"tabelaPrecos": [{"frequencia": 1, "valorCentavos": -1}]},
        {"tabelaPrecos": [{"frequencia": 1, "valorCentavos": 160.5}]},
        {"aulaAvulsaCentavos": -5},
        {"tabelaPrecos": "nao e lista"},
    ],
)
def test_config_invalida_400(dynamo_table, as_user, payload):
    as_user(ADMIN)
    assert client.put("/financeiro/config", json=payload).status_code == 400


def test_preco_zero_e_valido_na_tabela(dynamo_table, as_user):
    """Reposição de cortesia: preço 0 é uma escolha, não erro."""
    as_user(ADMIN)
    resp = client.put("/financeiro/config", json={"reposicaoCentavos": 0})
    assert resp.status_code == 200


# --- autorização e isolamento --------------------------------------------


@pytest.mark.parametrize(
    "metodo,url",
    [
        ("get", "/financeiro/mensalidades?mes=2026-10"),
        ("put", "/financeiro/planos/abc"),
        ("delete", "/financeiro/planos/abc"),
        ("get", "/financeiro/config"),
        ("put", "/financeiro/config"),
    ],
)
def test_membro_403_nas_rotas_novas(dynamo_table, as_user, metodo, url):
    as_user(MEMBRO)
    chamada = getattr(client, metodo)
    resp = chamada(url, json={"valorCentavos": 100}) if metodo == "put" else chamada(url)
    assert resp.status_code == 403


def test_clinica_b_nao_ve_mensalidades_da_a(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")
    _plano(pid, 26000)
    _pagar(pid, 26000)

    as_user(ADMIN_B)
    corpo = _mensalidades()
    assert corpo["alunos"] == []
    assert corpo["previstoCentavos"] == 0
    assert corpo["recebidoCentavos"] == 0


def test_clinica_b_nao_define_plano_de_aluno_da_a(dynamo_table, as_user):
    as_user(ADMIN)
    pid = _aluno("Marina Costa")

    as_user(ADMIN_B)
    assert _plano(pid, 99900).status_code == 404
