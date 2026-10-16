"""Testes dos endpoints da Agenda (marcações datadas, feature agenda)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OUTRA = {"X-Clinic-Id": "clinica-corpo"}


def _aluno(nome="Rebecca", headers=None, **extra):
    return client.post("/pacientes", json={"nome": nome, **extra}, headers=headers or {}).json()["id"]


def _agendar(headers=None, **dados):
    corpo = {"data": "2026-10-19", "hora": "07:00", **dados}
    return client.post("/agenda", json=corpo, headers=headers or {})


def _listar(de="2026-10-19", ate="2026-10-25", headers=None):
    return client.get(f"/agenda?de={de}&ate={ate}", headers=headers or {})


# --- Agendar paciente cadastrado ---


def test_agendar_paciente_retorna_201(dynamo_table):
    pid = _aluno(telefone="(91) 99999-0000")
    resp = _agendar(pacienteId=pid)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["data"] == "2026-10-19"
    assert body["hora"] == "07:00"
    assert body["nome"] == "Rebecca"
    assert body["telefone"] == "(91) 99999-0000"
    assert body["novo"] is False


def test_agendar_paciente_inexistente_retorna_404(dynamo_table):
    resp = _agendar(pacienteId="nao-existe")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Aluno não encontrado"


def test_agendar_paciente_duplicado_retorna_409(dynamo_table):
    pid = _aluno()
    assert _agendar(pacienteId=pid).status_code == 201
    resp = _agendar(pacienteId=pid)
    assert resp.status_code == 409
    assert len(_listar().json()) == 1


def test_mesmo_paciente_em_outra_data_ou_hora(dynamo_table):
    pid = _aluno()
    assert _agendar(pacienteId=pid).status_code == 201
    assert _agendar(pacienteId=pid, hora="08:00").status_code == 201
    assert _agendar(pacienteId=pid, data="2026-10-20").status_code == 201
    assert len(_listar().json()) == 3


# --- Agendar pessoa sem cadastro ---


def test_agendar_pessoa_nova(dynamo_table):
    resp = _agendar(nome="  João Experimental ", telefone="91 98888-7777")
    assert resp.status_code == 201
    body = resp.json()
    assert body["nome"] == "João Experimental"
    assert body["telefone"] == "91 98888-7777"
    assert body["novo"] is True
    assert body["pacienteId"] is None


def test_duas_pessoas_novas_no_mesmo_horario(dynamo_table):
    assert _agendar(nome="Ana").status_code == 201
    assert _agendar(nome="Bia").status_code == 201
    assert len(_listar().json()) == 2


def test_sem_paciente_e_sem_nome_retorna_400(dynamo_table):
    resp = _agendar(nome="   ")
    assert resp.status_code == 400
    assert "nome" in resp.json()["detail"]


def test_paciente_e_nome_juntos_retorna_400(dynamo_table):
    resp = _agendar(pacienteId=_aluno(), nome="Outro")
    assert resp.status_code == 400


# --- Validação de data/hora ---


def test_data_invalida_retorna_400(dynamo_table):
    assert _agendar(nome="Ana", data="2026-02-30").status_code == 400
    assert _agendar(nome="Ana", data="19/10/2026").status_code == 400


def test_hora_invalida_retorna_400(dynamo_table):
    assert _agendar(nome="Ana", hora="7:00").status_code == 400


# --- Listar ---


def test_listar_filtra_periodo_e_ordena(dynamo_table):
    _agendar(nome="Fora antes", data="2026-10-18")
    _agendar(nome="Zé", data="2026-10-20", hora="09:00")
    _agendar(nome="Ana", data="2026-10-20", hora="09:00")
    _agendar(nome="Cedo", data="2026-10-19", hora="06:00")
    _agendar(nome="Último dia", data="2026-10-25", hora="21:00")
    _agendar(nome="Fora depois", data="2026-10-26")
    nomes = [a["nome"] for a in _listar().json()]
    assert nomes == ["Cedo", "Ana", "Zé", "Último dia"]


def test_listar_usa_nome_ao_vivo_e_omite_removidos(dynamo_table):
    pid = _aluno()
    removido = _aluno("Saiu")
    _agendar(pacienteId=pid)
    _agendar(pacienteId=removido)
    client.put(f"/pacientes/{pid}", json={"nome": "Rebecca Lima"})
    client.delete(f"/pacientes/{removido}")
    nomes = [a["nome"] for a in _listar().json()]
    assert nomes == ["Rebecca Lima"]


def test_listar_periodo_invalido_retorna_400(dynamo_table):
    assert _listar(de="2026-10-25", ate="2026-10-19").status_code == 400
    assert _listar(de="2026-01-01", ate="2026-12-31").status_code == 400
    assert _listar(de="ontem").status_code == 400


def test_listar_isolado_por_clinica(dynamo_table):
    _agendar(nome="Ana")
    assert _listar(headers=OUTRA).json() == []


# --- Vincular pessoa nova a paciente ---


def test_vincular_pessoa_nova(dynamo_table):
    ag = _agendar(nome="João", telefone="9999").json()
    pid = _aluno("João Silva")
    resp = client.put(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", json={"pacienteId": pid})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pacienteId"] == pid
    assert body["nome"] == "João Silva"
    assert body["novo"] is False
    assert _listar().json()[0]["novo"] is False


def test_vincular_ja_vinculado_retorna_404(dynamo_table):
    pid = _aluno()
    ag = _agendar(pacienteId=pid).json()
    resp = client.put(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", json={"pacienteId": _aluno("B")})
    assert resp.status_code == 404


def test_vincular_paciente_inexistente_retorna_404(dynamo_table):
    ag = _agendar(nome="João").json()
    resp = client.put(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", json={"pacienteId": "nao-existe"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Aluno não encontrado"


# --- Desmarcar ---


def test_desmarcar(dynamo_table):
    ag = _agendar(nome="Ana").json()
    resp = client.delete(f"/agenda/{ag['data']}/07%3A00/{ag['id']}")
    assert resp.status_code == 200
    assert _listar().json() == []


def test_desmarcar_inexistente_retorna_404(dynamo_table):
    assert client.delete("/agenda/2026-10-19/07%3A00/nao-existe").status_code == 404


def test_desmarcar_de_outra_clinica_retorna_404(dynamo_table):
    ag = _agendar(nome="Ana").json()
    resp = client.delete(f"/agenda/{ag['data']}/07%3A00/{ag['id']}", headers=OUTRA)
    assert resp.status_code == 404
    assert len(_listar().json()) == 1


def test_desmarcar_hora_invalida_retorna_400(dynamo_table):
    assert client.delete("/agenda/2026-10-19/7h/abc").status_code == 400


# --- Pagamento da aula (Receber → entrada no Caixa) ---


@pytest.fixture
def admin():
    """Usuário admin — os testes conferem o resultado na tela de Caixa (/financeiro),
    que é só de admin. O "Receber" em si não exige admin (ver teste do membro)."""
    from app.deps import get_current_role

    app.dependency_overrides[get_current_role] = lambda: "admin"
    yield
    app.dependency_overrides.pop(get_current_role, None)


def _url(ag):
    return f"/agenda/{ag['data']}/07%3A00/{ag['id']}"


def _receber(ag, headers=None, **dados):
    corpo = {"tipoAula": "avulsa", "valorCentavos": 8000, "formaPagamento": "pix",
             "dataPagamento": "2026-10-16", **dados}
    return client.post(f"{_url(ag)}/pagamento", json=corpo, headers=headers or {})


def _caixa(mes="2026-10"):
    return client.get(f"/financeiro/lancamentos?mes={mes}").json()


def test_receber_lanca_entrada_no_caixa(dynamo_table, admin):
    ag = _agendar(nome="João").json()
    resp = _receber(ag)
    assert resp.status_code == 200
    pag = resp.json()["pagamento"]
    assert pag["valorCentavos"] == 8000
    assert pag["formaPagamento"] == "pix"
    assert pag["tipoAula"] == "avulsa"
    assert pag["dataPagamento"] == "2026-10-16"

    caixa = _caixa()
    assert caixa["entradasCentavos"] == 8000
    lanc = caixa["lancamentos"][0]
    assert lanc["tipo"] == "entrada"
    assert lanc["descricao"] == "Aula avulsa — João (19/10 às 07:00)"
    assert _listar().json()[0]["pagamento"]["lancamentoId"] == lanc["id"]


def test_receber_de_paciente_nao_conta_como_mensalidade(dynamo_table, admin):
    pid = _aluno()
    ag = _agendar(pacienteId=pid).json()
    _receber(ag, tipoAula="reposicao", valorCentavos=5000)
    lanc = _caixa()["lancamentos"][0]
    assert lanc["pacienteId"] == pid
    assert lanc["competencia"] is None
    assert lanc["descricao"].startswith("Reposição — Rebecca")


def test_receber_duas_vezes_retorna_409(dynamo_table, admin):
    ag = _agendar(nome="João").json()
    assert _receber(ag).status_code == 200
    assert _receber(ag).status_code == 409
    assert _caixa()["entradasCentavos"] == 8000


def test_receber_valor_invalido_retorna_400(dynamo_table, admin):
    ag = _agendar(nome="João").json()
    assert _receber(ag, valorCentavos=80.5).status_code == 400
    assert _receber(ag, valorCentavos=0).status_code == 400
    assert _receber(ag, formaPagamento="cheque").status_code == 400
    assert _receber(ag, tipoAula="mensal").status_code == 400
    assert _caixa()["lancamentos"] == []


def test_receber_marcacao_inexistente_retorna_404(dynamo_table):
    ag = {"data": "2026-10-19", "id": "nao-existe"}
    assert _receber(ag).status_code == 404


def test_receber_liberado_para_membro(dynamo_table):
    """Membro não vê o Caixa (/financeiro é só admin), mas pode receber a aula."""
    from app.deps import get_current_role

    app.dependency_overrides[get_current_role] = lambda: "membro"
    try:
        ag = _agendar(nome="João").json()
        assert _receber(ag).status_code == 200
        assert client.get("/agenda/precos").status_code == 200
        assert client.get("/financeiro/lancamentos").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_role, None)


def test_desfazer_pagamento_cancela_lancamento(dynamo_table, admin):
    ag = _agendar(nome="João").json()
    _receber(ag)
    resp = client.delete(f"{_url(ag)}/pagamento")
    assert resp.status_code == 200
    assert resp.json()["pagamento"] is None
    assert _caixa()["lancamentos"] == []
    assert _listar().json()[0]["pagamento"] is None
    # e pode receber de novo
    assert _receber(ag).status_code == 200


def test_cancelar_no_caixa_tira_o_pago_da_agenda(dynamo_table, admin):
    ag = _agendar(nome="João").json()
    lanc_id = _receber(ag).json()["pagamento"]["lancamentoId"]
    assert client.delete(f"/financeiro/lancamentos/2026-10/{lanc_id}").status_code == 200
    assert _listar().json()[0]["pagamento"] is None
    assert _receber(ag).status_code == 200  # receber de novo é permitido
    assert _caixa()["entradasCentavos"] == 8000


def test_editar_valor_no_caixa_reflete_na_agenda(dynamo_table, admin):
    ag = _agendar(nome="João").json()
    lanc_id = _receber(ag).json()["pagamento"]["lancamentoId"]
    client.put(
        f"/financeiro/lancamentos/2026-10/{lanc_id}",
        json={"tipo": "entrada", "data": "2026-10-16", "valorCentavos": 9000,
              "descricao": "Aula avulsa — João", "formaPagamento": "dinheiro"},
    )
    pag = _listar().json()[0]["pagamento"]
    assert pag["valorCentavos"] == 9000
    assert pag["formaPagamento"] == "dinheiro"


def test_desmarcar_aula_paga_retorna_409(dynamo_table):
    ag = _agendar(nome="João").json()
    _receber(ag)
    resp = client.delete(_url(ag))
    assert resp.status_code == 409
    assert len(_listar().json()) == 1
    client.delete(f"{_url(ag)}/pagamento")
    assert client.delete(_url(ag)).status_code == 200


def test_precos_vem_da_tabela_do_financeiro(dynamo_table, admin):
    client.put("/financeiro/config", json={"aulaAvulsaCentavos": 8000, "reposicaoCentavos": 5000})
    assert client.get("/agenda/precos").json() == {"aulaAvulsaCentavos": 8000, "reposicaoCentavos": 5000}


# --- Retenção de 4 meses (TTL) ---


def test_expira_em_4_meses_apos_a_data_da_aula():
    from datetime import datetime, timezone

    from app.repository_agenda import expira_em

    def em(epoch):
        return datetime.fromtimestamp(epoch, timezone.utc).date().isoformat()

    assert em(expira_em("2026-10-19")) == "2027-02-19"
    assert em(expira_em("2026-10-31")) == "2027-02-28"  # fevereiro não tem 31
    assert em(expira_em("2026-06-30")) == "2026-10-30"


def test_item_grava_expira_em_e_nao_o_expoe(dynamo_table):
    import boto3

    from app.repository_agenda import expira_em

    body = _agendar(nome="Ana").json()
    assert "expiraEm" not in body
    item = boto3.resource("dynamodb").Table(dynamo_table).scan()["Items"][0]
    assert int(item["expiraEm"]) == expira_em("2026-10-19")


def test_listar_omite_vencidos_que_o_ttl_ainda_nao_apagou(dynamo_table):
    """O TTL do DynamoDB apaga com atraso; a lista não pode mostrar o vencido."""
    _agendar(nome="Antiga", data="2020-01-06")
    _agendar(nome="Recente", data="2020-01-07")
    import boto3

    tabela = boto3.resource("dynamodb").Table(dynamo_table)
    for i in tabela.scan()["Items"]:
        if i["nome"] == "Recente":
            tabela.update_item(
                Key={"PK": i["PK"], "SK": i["SK"]},
                UpdateExpression="SET expiraEm = :e",
                ExpressionAttributeValues={":e": 4102444800},  # 2100-01-01
            )
    nomes = [a["nome"] for a in _listar(de="2020-01-06", ate="2020-01-12").json()]
    assert nomes == ["Recente"]
