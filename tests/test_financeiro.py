"""Testes dos endpoints do Fluxo de Caixa (FIN-01/03/04/05/06/07/10/11).

O `require_admin` lê a claim `custom:role`, que só existe quando há authorizer. Como nos
testes não há, cada teste declara o usuário logado com a fixture `as_user` — o mesmo
padrão de `test_membros.py`.
"""
import pytest
from fastapi.testclient import TestClient

from app.deps import get_claims, get_clinic_id
from app.main import app

client = TestClient(app)

ADMIN = {"custom:clinicId": "clinica-a", "custom:role": "admin"}
ADMIN_B = {"custom:clinicId": "clinica-b", "custom:role": "admin"}
MEMBRO = {"custom:clinicId": "clinica-a", "custom:role": "membro"}
SEM_ROLE = {"custom:clinicId": "clinica-a"}
SEM_CLINICA = {"custom:role": "admin"}

LANCAMENTO = {
    "tipo": "saida",
    "data": "2026-10-05",
    "valorCentavos": 15000,
    "descricao": "Conta de luz",
    "formaPagamento": "pix",
}


@pytest.fixture
def as_user():
    """Simula o usuário logado sobrescrevendo as claims (raiz da cadeia de auth)."""

    def _set(claims):
        app.dependency_overrides.pop(get_clinic_id, None)
        app.dependency_overrides[get_claims] = lambda: claims

    yield _set
    app.dependency_overrides.pop(get_claims, None)


def _criar(**over):
    return client.post("/financeiro/lancamentos", json={**LANCAMENTO, **over})


def _caixa(mes="2026-10"):
    return client.get(f"/financeiro/lancamentos?mes={mes}")


# --- criação (FIN-01) -----------------------------------------------------


def test_criar_lancamento_201(dynamo_table, as_user):
    as_user(ADMIN)
    resp = _criar()

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["id"]
    assert corpo["valorCentavos"] == 15000
    assert corpo["descricao"] == "Conta de luz"


def test_criado_aparece_no_caixa(dynamo_table, as_user):
    as_user(ADMIN)
    _criar()

    corpo = _caixa().json()
    assert len(corpo["lancamentos"]) == 1
    assert corpo["lancamentos"][0]["descricao"] == "Conta de luz"


def test_saida_nao_vaza_campos_internos(dynamo_table, as_user):
    as_user(ADMIN)
    corpo = _criar().json()
    assert "clinicId" not in corpo
    assert "ativo" not in corpo


def test_lancamento_cai_no_mes_da_data_nao_no_de_hoje(dynamo_table, as_user):
    as_user(ADMIN)
    _criar(data="2026-09-28")

    assert _caixa("2026-10").json()["lancamentos"] == []
    assert len(_caixa("2026-09").json()["lancamentos"]) == 1


# --- validações (FIN-05) --------------------------------------------------


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("tipo", "receita"),
        ("valorCentavos", 0),
        ("valorCentavos", -100),
        ("valorCentavos", 150.5),
        ("data", "2026-02-30"),
        ("data", "28/09/2026"),
        ("descricao", "   "),
        ("descricao", "x" * 201),
        ("formaPagamento", "boleto"),
    ],
)
def test_payload_invalido_400(dynamo_table, as_user, campo, valor):
    as_user(ADMIN)
    resp = _criar(**{campo: valor})
    assert resp.status_code == 400
    assert resp.json()["detail"]


def test_competencia_sem_paciente_400(dynamo_table, as_user):
    as_user(ADMIN)
    resp = _criar(tipo="entrada", competencia="2026-10")
    assert resp.status_code == 400


def test_mes_invalido_no_get_400(dynamo_table, as_user):
    as_user(ADMIN)
    resp = _caixa("2026-13")
    assert resp.status_code == 400
    assert "AAAA-MM" in resp.json()["detail"]


# --- caixa do mês e totais (FIN-03, FIN-04) -------------------------------


def test_mes_vazio_200_com_zeros(dynamo_table, as_user):
    as_user(ADMIN)
    corpo = _caixa().json()

    assert corpo["mes"] == "2026-10"
    assert corpo["entradasCentavos"] == 0
    assert corpo["saidasCentavos"] == 0
    assert corpo["saldoCentavos"] == 0
    assert corpo["lancamentos"] == []


def test_totais_e_saldo(dynamo_table, as_user):
    as_user(ADMIN)
    _criar(tipo="entrada", valorCentavos=10000, descricao="Avulsa")
    _criar(tipo="entrada", valorCentavos=26000, descricao="Mensalidade")
    _criar(tipo="saida", valorCentavos=15000, descricao="Luz")

    corpo = _caixa().json()
    assert corpo["entradasCentavos"] == 36000
    assert corpo["saidasCentavos"] == 15000
    assert corpo["saldoCentavos"] == 21000


def test_saldo_negativo(dynamo_table, as_user):
    as_user(ADMIN)
    _criar(tipo="entrada", valorCentavos=10000)
    _criar(tipo="saida", valorCentavos=25000)

    assert _caixa().json()["saldoCentavos"] == -15000


def test_extrato_ordenado_por_data(dynamo_table, as_user):
    as_user(ADMIN)
    _criar(data="2026-10-20", descricao="c")
    _criar(data="2026-10-01", descricao="a")
    _criar(data="2026-10-10", descricao="b")

    descricoes = [l["descricao"] for l in _caixa().json()["lancamentos"]]
    assert descricoes == ["a", "b", "c"]


def test_mes_ausente_usa_mes_corrente(dynamo_table, as_user):
    from datetime import datetime, timezone

    as_user(ADMIN)
    resp = client.get("/financeiro/lancamentos")

    assert resp.status_code == 200
    assert resp.json()["mes"] == datetime.now(timezone.utc).strftime("%Y-%m")


# --- edição (FIN-10) ------------------------------------------------------


def test_editar_valor_muda_o_total(dynamo_table, as_user):
    as_user(ADMIN)
    lanc_id = _criar().json()["id"]

    resp = client.put(
        f"/financeiro/lancamentos/2026-10/{lanc_id}",
        json={**LANCAMENTO, "valorCentavos": 18000},
    )
    assert resp.status_code == 200
    assert resp.json()["valorCentavos"] == 18000
    assert _caixa().json()["saidasCentavos"] == 18000


def test_editar_mudando_de_mes_400(dynamo_table, as_user):
    as_user(ADMIN)
    lanc_id = _criar().json()["id"]

    resp = client.put(
        f"/financeiro/lancamentos/2026-10/{lanc_id}",
        json={**LANCAMENTO, "data": "2026-09-30"},
    )
    assert resp.status_code == 400
    assert "outro mês" in resp.json()["detail"]


def test_editar_data_dentro_do_mes_ok(dynamo_table, as_user):
    as_user(ADMIN)
    lanc_id = _criar().json()["id"]

    resp = client.put(
        f"/financeiro/lancamentos/2026-10/{lanc_id}",
        json={**LANCAMENTO, "data": "2026-10-03"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == "2026-10-03"


def test_editar_inexistente_404(dynamo_table, as_user):
    as_user(ADMIN)
    resp = client.put("/financeiro/lancamentos/2026-10/nao-existe", json=LANCAMENTO)
    assert resp.status_code == 404


# --- cancelamento (FIN-11) ------------------------------------------------


def test_cancelar_some_da_lista_e_do_total(dynamo_table, as_user):
    as_user(ADMIN)
    lanc_id = _criar().json()["id"]
    _criar(descricao="fica")

    resp = client.delete(f"/financeiro/lancamentos/2026-10/{lanc_id}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Lançamento cancelado"

    corpo = _caixa().json()
    assert [l["descricao"] for l in corpo["lancamentos"]] == ["fica"]
    assert corpo["saidasCentavos"] == 15000


def test_cancelar_duas_vezes_404(dynamo_table, as_user):
    as_user(ADMIN)
    lanc_id = _criar().json()["id"]

    assert client.delete(f"/financeiro/lancamentos/2026-10/{lanc_id}").status_code == 200
    assert client.delete(f"/financeiro/lancamentos/2026-10/{lanc_id}").status_code == 404


def test_cancelar_inexistente_404(dynamo_table, as_user):
    as_user(ADMIN)
    assert client.delete("/financeiro/lancamentos/2026-10/nao-existe").status_code == 404


def test_editar_cancelado_404(dynamo_table, as_user):
    as_user(ADMIN)
    lanc_id = _criar().json()["id"]
    client.delete(f"/financeiro/lancamentos/2026-10/{lanc_id}")

    resp = client.put(f"/financeiro/lancamentos/2026-10/{lanc_id}", json=LANCAMENTO)
    assert resp.status_code == 404


# --- autorização: só admin (FIN-06) --------------------------------------


@pytest.mark.parametrize(
    "metodo,url",
    [
        ("get", "/financeiro/lancamentos?mes=2026-10"),
        ("post", "/financeiro/lancamentos"),
        ("put", "/financeiro/lancamentos/2026-10/abc"),
        ("delete", "/financeiro/lancamentos/2026-10/abc"),
    ],
)
def test_membro_recebe_403_em_todas_as_rotas(dynamo_table, as_user, metodo, url):
    as_user(MEMBRO)
    resp = getattr(client, metodo)(url, json=LANCAMENTO) if metodo in ("post", "put") else getattr(client, metodo)(url)
    assert resp.status_code == 403


def test_sem_role_403_fail_closed(dynamo_table, as_user):
    as_user(SEM_ROLE)
    assert _caixa().status_code == 403


def test_sem_clinica_401(dynamo_table, as_user):
    as_user(SEM_CLINICA)
    assert _caixa().status_code == 401


def test_membro_nao_consegue_criar_nem_de_raspao(dynamo_table, as_user):
    """403 tem que barrar ANTES de escrever: nada pode sobrar na tabela."""
    as_user(MEMBRO)
    assert _criar().status_code == 403

    as_user(ADMIN)
    assert _caixa().json()["lancamentos"] == []


# --- isolamento multi-tenant (FIN-07) ------------------------------------


def test_clinica_b_nao_ve_o_caixa_da_a(dynamo_table, as_user):
    as_user(ADMIN)
    _criar()

    as_user(ADMIN_B)
    corpo = _caixa().json()
    assert corpo["lancamentos"] == []
    assert corpo["saldoCentavos"] == 0


def test_clinica_b_nao_edita_nem_cancela_da_a(dynamo_table, as_user):
    as_user(ADMIN)
    lanc_id = _criar().json()["id"]

    as_user(ADMIN_B)
    assert client.put(f"/financeiro/lancamentos/2026-10/{lanc_id}", json=LANCAMENTO).status_code == 404
    assert client.delete(f"/financeiro/lancamentos/2026-10/{lanc_id}").status_code == 404

    as_user(ADMIN)
    assert len(_caixa().json()["lancamentos"]) == 1


# --- sem regressão --------------------------------------------------------


def test_health_continua_publico():
    assert client.get("/health").json() == {"status": "ok"}
