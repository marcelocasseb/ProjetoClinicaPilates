"""Testes dos schemas Pydantic de Avaliação (AVL-03, AVL-10)."""
import pytest
from pydantic import ValidationError

from app.schemas_avaliacao import AvaliacaoCreate, AvaliacaoOut, AvaliacaoUpdate


def test_cria_vazia_e_valida():
    # cadastro flexível: nenhum campo clínico é obrigatório
    a = AvaliacaoCreate()
    assert a.data is None
    assert a.queixaPrincipal is None
    assert a.avaliacaoPostural is None
    assert a.medidas is None


def test_texto_so_espacos_vira_none():
    a = AvaliacaoCreate(queixaPrincipal="   ", hma="  dor  ")
    assert a.queixaPrincipal is None
    assert a.hma == "dor"


def test_data_valida_aceita():
    assert AvaliacaoCreate(data="2026-07-22").data == "2026-07-22"


def test_data_vazia_vira_none():
    assert AvaliacaoCreate(data="   ").data is None


def test_data_invalida_rejeitada():
    with pytest.raises(ValidationError):
        AvaliacaoCreate(data="22/07/2026")


def test_data_nao_string_rejeitada():
    with pytest.raises(ValidationError):
        AvaliacaoCreate(data=20260722)


def test_avaliacao_postural_preenchida():
    a = AvaliacaoCreate(avaliacaoPostural={"vistaAnterior": "ombros elevados"})
    assert a.avaliacaoPostural.vistaAnterior == "ombros elevados"
    assert a.avaliacaoPostural.vistaPosterior is None


def test_avaliacao_postural_toda_vazia_vira_none():
    a = AvaliacaoCreate(avaliacaoPostural={"vistaAnterior": "  ", "vistaPosterior": ""})
    assert a.avaliacaoPostural is None


def test_medidas_preenchidas_e_vazias():
    assert AvaliacaoCreate(medidas={"braco": "30cm"}).medidas.braco == "30cm"
    assert AvaliacaoCreate(medidas={"braco": "   "}).medidas is None


def test_campos_desconhecidos_ignorados():
    a = AvaliacaoCreate(queixaPrincipal="x", lixo="y")
    assert not hasattr(a, "lixo")


def test_update_tambem_valida_data():
    with pytest.raises(ValidationError):
        AvaliacaoUpdate(data="ontem")


def test_avaliacao_out_monta():
    out = AvaliacaoOut(
        id="abc",
        pacienteId="p1",
        data="2026-07-22",
        queixaPrincipal="dor lombar",
        ativo=True,
        criadoEm="2026-07-22T10:00:00Z",
        atualizadoEm="2026-07-22T10:00:00Z",
    )
    assert out.id == "abc"
    assert out.pacienteId == "p1"
    assert out.queixaPrincipal == "dor lombar"
