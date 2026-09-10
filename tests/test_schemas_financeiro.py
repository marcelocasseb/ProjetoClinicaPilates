"""Testes dos schemas do Fluxo de Caixa (FIN-01, FIN-05, FIN-12)."""
import pytest
from pydantic import ValidationError

from app.schemas_financeiro import (
    CaixaMesOut,
    LancamentoCreate,
    LancamentoOut,
    LancamentoUpdate,
    valida_mes,
)

VALIDO = {
    "tipo": "saida",
    "data": "2026-09-28",
    "valorCentavos": 15000,
    "descricao": "Conta de luz",
}


def _cria(**over):
    return LancamentoCreate(**{**VALIDO, **over})


# --- tipo -----------------------------------------------------------------


@pytest.mark.parametrize("tipo", ["entrada", "saida"])
def test_tipo_valido(tipo):
    assert _cria(tipo=tipo).tipo == tipo


def test_tipo_normaliza_caixa_e_espaco():
    assert _cria(tipo="  ENTRADA ").tipo == "entrada"


@pytest.mark.parametrize("tipo", ["receita", "", "  ", None, 1, "entradas"])
def test_tipo_invalido(tipo):
    with pytest.raises(ValidationError):
        _cria(tipo=tipo)


# --- valorCentavos --------------------------------------------------------


def test_valor_inteiro_positivo():
    assert _cria(valorCentavos=1).valorCentavos == 1


def test_valor_string_numerica_vira_int():
    lanc = _cria(valorCentavos="15000")
    assert lanc.valorCentavos == 15000
    assert isinstance(lanc.valorCentavos, int)


@pytest.mark.parametrize("valor", [0, -1, -15000])
def test_valor_nao_positivo_recusado(valor):
    with pytest.raises(ValidationError):
        _cria(valorCentavos=valor)


@pytest.mark.parametrize("valor", [15000.5, 15000.0, 0.1])
def test_valor_float_recusado(valor):
    """Dinheiro é inteiro em centavos — float é sintoma de bug, não de arredondamento."""
    with pytest.raises(ValidationError):
        _cria(valorCentavos=valor)


def test_valor_booleano_recusado():
    """`True` é `int` em Python e viraria 1 centavo sem a guarda explícita."""
    with pytest.raises(ValidationError):
        _cria(valorCentavos=True)


@pytest.mark.parametrize("valor", ["150,00", "150.00", "abc", "", None, "-5"])
def test_valor_string_invalida_recusada(valor):
    with pytest.raises(ValidationError):
        _cria(valorCentavos=valor)


# --- data -----------------------------------------------------------------


def test_data_valida():
    assert _cria(data="2026-10-05").data == "2026-10-05"


def test_data_futura_aceita():
    """Pagamento adiantado é normal — a data futura cai na partição do mês dela."""
    assert _cria(data="2099-01-15").data == "2099-01-15"


def test_data_bissexta_valida():
    assert _cria(data="2028-02-29").data == "2028-02-29"


@pytest.mark.parametrize(
    "data",
    ["2026-02-30", "2026-13-01", "2026-00-10", "2027-02-29"],
)
def test_data_inexistente_recusada(data):
    with pytest.raises(ValidationError):
        _cria(data=data)


@pytest.mark.parametrize("data", ["28/09/2026", "2026-9-28", "20260928", "", None, "hoje"])
def test_data_formato_invalido(data):
    with pytest.raises(ValidationError):
        _cria(data=data)


# --- descricao ------------------------------------------------------------


def test_descricao_trimada():
    assert _cria(descricao="  Aluguel  ").descricao == "Aluguel"


def test_descricao_no_limite_aceita():
    assert len(_cria(descricao="x" * 200).descricao) == 200


@pytest.mark.parametrize("desc", ["", "   ", None, 42])
def test_descricao_obrigatoria(desc):
    with pytest.raises(ValidationError):
        _cria(descricao=desc)


def test_descricao_longa_demais_recusada():
    with pytest.raises(ValidationError):
        _cria(descricao="x" * 201)


# --- formaPagamento -------------------------------------------------------


@pytest.mark.parametrize("forma", ["dinheiro", "pix", "cartao", "transferencia"])
def test_forma_pagamento_valida(forma):
    assert _cria(formaPagamento=forma).formaPagamento == forma


def test_forma_pagamento_ausente_vira_none():
    assert _cria().formaPagamento is None
    assert _cria(formaPagamento="   ").formaPagamento is None


def test_forma_pagamento_invalida():
    with pytest.raises(ValidationError):
        _cria(formaPagamento="boleto")


# --- pacienteId / competencia (preparação F2, FIN-12) ---------------------


def test_paciente_e_competencia_juntos_aceitos():
    lanc = _cria(tipo="entrada", pacienteId="p1", competencia="2026-10")
    assert lanc.pacienteId == "p1"
    assert lanc.competencia == "2026-10"


def test_paciente_sozinho_aceito():
    """Aula avulsa de um aluno: tem paciente, não tem competência."""
    assert _cria(pacienteId="p1").competencia is None


def test_competencia_sem_paciente_recusada():
    with pytest.raises(ValidationError):
        _cria(competencia="2026-10")


@pytest.mark.parametrize("comp", ["2026-13", "2026-1", "10/2026", "2026"])
def test_competencia_formato_invalido(comp):
    with pytest.raises(ValidationError):
        _cria(pacienteId="p1", competencia=comp)


# --- extras ---------------------------------------------------------------


def test_campos_desconhecidos_ignorados():
    lanc = _cria(saldoFinal=999, clinicId="outra")
    assert not hasattr(lanc, "saldoFinal")
    assert not hasattr(lanc, "clinicId")


def test_update_tem_a_mesma_validacao_do_create():
    with pytest.raises(ValidationError):
        LancamentoUpdate(**{**VALIDO, "valorCentavos": 0})
    assert LancamentoUpdate(**VALIDO).valorCentavos == 15000


# --- valida_mes -----------------------------------------------------------


@pytest.mark.parametrize("mes", ["2026-01", "2026-12", " 2026-10 "])
def test_valida_mes_ok(mes):
    assert valida_mes(mes) == mes.strip()


@pytest.mark.parametrize("mes", ["2026-13", "2026-00", "2026-1", "10-2026", "", None, 202610])
def test_valida_mes_invalido(mes):
    with pytest.raises(ValueError):
        valida_mes(mes)


# --- saída ----------------------------------------------------------------


def test_lancamento_out_aceita_item_do_repositorio():
    out = LancamentoOut(
        id="abc",
        tipo="entrada",
        data="2026-10-05",
        valorCentavos=26000,
        descricao="Mensalidade Rebecca",
        clinicId="ignorado",
        ativo=True,
    )
    assert out.id == "abc"
    assert not hasattr(out, "ativo")


def test_caixa_mes_out():
    caixa = CaixaMesOut(
        mes="2026-10",
        entradasCentavos=36000,
        saidasCentavos=15000,
        saldoCentavos=21000,
        lancamentos=[],
    )
    assert caixa.saldoCentavos == 21000
