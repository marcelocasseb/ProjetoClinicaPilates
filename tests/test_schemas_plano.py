"""Testes dos schemas de Plano e Tabela de preços (fluxo-caixa F2)."""
import pytest
from pydantic import ValidationError

from app.schemas_plano import ConfigPrecos, FaixaPreco, PlanoUpsert


def _plano(**over):
    return PlanoUpsert(**{"valorCentavos": 26000, **over})


# --- valor: zero é VÁLIDO aqui (diferente do lançamento) ------------------


def test_valor_zero_aceito():
    """Bolsista/cortesia. No lançamento zero é erro; no plano é uma escolha."""
    assert _plano(valorCentavos=0).valorCentavos == 0


def test_valor_string_numerica():
    assert _plano(valorCentavos="26000").valorCentavos == 26000


@pytest.mark.parametrize("v", [-1, 260.5, 260.0, True, "abc", "260,00", None])
def test_valor_invalido(v):
    with pytest.raises(ValidationError):
        _plano(valorCentavos=v)


# --- diaVencimento --------------------------------------------------------


@pytest.mark.parametrize("d", [1, 15, 31, "5"])
def test_dia_vencimento_valido(d):
    assert _plano(diaVencimento=d).diaVencimento == int(d)


@pytest.mark.parametrize("d", [0, 32, -1, "abc"])
def test_dia_vencimento_invalido(d):
    with pytest.raises(ValidationError):
        _plano(diaVencimento=d)


@pytest.mark.parametrize("d", [None, ""])
def test_dia_vencimento_opcional(d):
    assert _plano(diaVencimento=d).diaVencimento is None


# --- frequencia -----------------------------------------------------------


@pytest.mark.parametrize("f", [1, 7, "3"])
def test_frequencia_valida(f):
    assert _plano(frequencia=f).frequencia == int(f)


@pytest.mark.parametrize("f", [0, 8, -2, "x"])
def test_frequencia_invalida(f):
    with pytest.raises(ValidationError):
        _plano(frequencia=f)


def test_frequencia_opcional():
    assert _plano().frequencia is None


# --- observacao -----------------------------------------------------------


def test_observacao_trimada_e_vazia_vira_none():
    assert _plano(observacao="  bolsa integral ").observacao == "bolsa integral"
    assert _plano(observacao="   ").observacao is None


def test_observacao_longa_recusada():
    with pytest.raises(ValidationError):
        _plano(observacao="x" * 201)


def test_campos_desconhecidos_ignorados():
    p = _plano(pacienteId="p1", ativo=False)
    assert not hasattr(p, "pacienteId")


# --- tabela de preços -----------------------------------------------------


def test_faixa_valida():
    f = FaixaPreco(frequencia=2, valorCentavos=26000)
    assert f.frequencia == 2


@pytest.mark.parametrize("freq", [0, 8, "x", None])
def test_faixa_frequencia_invalida(freq):
    with pytest.raises(ValidationError):
        FaixaPreco(frequencia=freq, valorCentavos=26000)


def test_config_vazia_e_valida():
    cfg = ConfigPrecos()
    assert cfg.tabelaPrecos == []
    assert cfg.aulaAvulsaCentavos == 0
    assert cfg.reposicaoCentavos == 0


def test_config_completa():
    cfg = ConfigPrecos(
        tabelaPrecos=[{"frequencia": 1, "valorCentavos": 16000}],
        aulaAvulsaCentavos=5000,
        reposicaoCentavos=0,
    )
    assert cfg.tabelaPrecos[0].valorCentavos == 16000
    assert cfg.aulaAvulsaCentavos == 5000


def test_config_tabela_nao_lista():
    with pytest.raises(ValidationError):
        ConfigPrecos(tabelaPrecos="nao e lista")


@pytest.mark.parametrize("v", [-1, 50.5, "abc"])
def test_config_preco_avulso_invalido(v):
    with pytest.raises(ValidationError):
        ConfigPrecos(aulaAvulsaCentavos=v)


@pytest.mark.parametrize("v", [None, ""])
def test_config_preco_avulso_ausente_vira_zero(v):
    assert ConfigPrecos(aulaAvulsaCentavos=v).aulaAvulsaCentavos == 0
