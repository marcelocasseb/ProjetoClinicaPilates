"""Testes dos schemas Pydantic de Paciente (PAC-03, PAC-04, PAC-09)."""
import pytest
from pydantic import ValidationError

from app.schemas import PacienteCreate, PacienteOut, PacienteUpdate


def test_cria_com_apenas_nome():
    p = PacienteCreate(nome="Maria")
    assert p.nome == "Maria"
    assert p.email is None
    assert p.dataNascimento is None


def test_nome_com_espacos_ao_redor_e_trimado():
    assert PacienteCreate(nome="  João  ").nome == "João"


def test_nome_ausente_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate()


def test_nome_so_espacos_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="   ")


def test_email_invalido_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", email="nao-eh-email")


def test_email_valido_aceito():
    assert PacienteCreate(nome="Ana", email="ana@clinica.com").email == "ana@clinica.com"


def test_email_vazio_vira_none():
    assert PacienteCreate(nome="Ana", email="   ").email is None


def test_telefone_vazio_vira_none():
    assert PacienteCreate(nome="Ana", telefone="").telefone is None


def test_data_nascimento_formato_invalido_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", dataNascimento="20-01-1990")


def test_data_nascimento_calendario_invalido_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", dataNascimento="1990-13-40")


def test_data_nascimento_valida_aceita():
    assert PacienteCreate(nome="Ana", dataNascimento="1990-05-12").dataNascimento == "1990-05-12"


def test_campos_desconhecidos_sao_ignorados():
    p = PacienteCreate(nome="Ana", campoLixo="x")
    assert not hasattr(p, "campoLixo")


def test_update_tambem_exige_nome():
    with pytest.raises(ValidationError):
        PacienteUpdate(nome="")


def test_paciente_out_monta_do_item():
    out = PacienteOut(
        id="abc",
        nome="Ana",
        ativo=True,
        criadoEm="2026-07-20T10:00:00Z",
        atualizadoEm="2026-07-20T10:00:00Z",
    )
    assert out.id == "abc"
    assert out.ativo is True
