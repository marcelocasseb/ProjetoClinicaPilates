"""Testes dos schemas Pydantic de Aparelho (APR-03, APR-09)."""
import pytest
from pydantic import ValidationError

from app.schemas_aparelho import AparelhoCreate, AparelhoOut, AparelhoUpdate


def test_cria_com_apenas_nome():
    a = AparelhoCreate(nome="Reformer")
    assert a.nome == "Reformer"
    assert a.categoria is None
    assert a.descricao is None


def test_nome_trimado():
    assert AparelhoCreate(nome="  Cadillac  ").nome == "Cadillac"


def test_nome_ausente_rejeitado():
    with pytest.raises(ValidationError):
        AparelhoCreate()


def test_nome_so_espacos_rejeitado():
    with pytest.raises(ValidationError):
        AparelhoCreate(nome="   ")


def test_categoria_e_descricao_aceitas():
    a = AparelhoCreate(nome="Chair", categoria="Cadeira", descricao="Wunda chair preta")
    assert a.categoria == "Cadeira"
    assert a.descricao == "Wunda chair preta"


def test_categoria_vazia_vira_none():
    assert AparelhoCreate(nome="Barrel", categoria="   ").categoria is None


def test_campos_desconhecidos_ignorados():
    a = AparelhoCreate(nome="Mat", lixo="x")
    assert not hasattr(a, "lixo")


def test_update_tambem_exige_nome():
    with pytest.raises(ValidationError):
        AparelhoUpdate(nome="")


def test_aparelho_out_monta():
    out = AparelhoOut(
        id="abc",
        nome="Reformer",
        categoria="Reformer",
        ativo=True,
        criadoEm="2026-07-21T10:00:00Z",
        atualizadoEm="2026-07-21T10:00:00Z",
    )
    assert out.id == "abc"
    assert out.ativo is True
