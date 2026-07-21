"""Testes dos schemas Pydantic de Paciente (PAC-03, PAC-04, PAC-09; AD-008 cpf, AD-009 endereço)."""
import pytest
from pydantic import ValidationError

from app.schemas import Endereco, PacienteCreate, PacienteOut, PacienteUpdate

# CPF de teste válido (dígitos verificadores corretos)
CPF_VALIDO = "529.982.247-25"


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


# --- CPF (AD-008) ---


def test_cpf_valido_normalizado():
    # entra formatado, sai só com dígitos
    assert PacienteCreate(nome="Ana", cpf=CPF_VALIDO).cpf == "52998224725"


def test_cpf_invalido_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", cpf="52998224726")  # último dígito errado


def test_cpf_todos_iguais_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", cpf="11111111111")


def test_cpf_tamanho_errado_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", cpf="123")


def test_cpf_vazio_vira_none():
    assert PacienteCreate(nome="Ana", cpf="   ").cpf is None


# --- Endereço MAP (AD-009) ---


def test_endereco_objeto_aceito():
    p = PacienteCreate(
        nome="Ana",
        endereco={
            "cep": "01310-100",
            "logradouro": "Av. Paulista",
            "numero": "1000",
            "bairro": "Bela Vista",
            "cidade": "São Paulo",
            "uf": "sp",
        },
    )
    assert isinstance(p.endereco, Endereco)
    assert p.endereco.cep == "01310100"  # normalizado só dígitos
    assert p.endereco.uf == "SP"  # normalizado maiúsculo
    assert p.endereco.cidade == "São Paulo"


def test_endereco_cep_invalido_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", endereco={"cep": "1234"})


def test_endereco_uf_invalida_rejeitada():
    with pytest.raises(ValidationError):
        PacienteCreate(nome="Ana", endereco={"uf": "XYZ"})


def test_endereco_vazio_vira_none():
    assert PacienteCreate(nome="Ana", endereco={}).endereco is None


def test_endereco_ausente_e_none():
    assert PacienteCreate(nome="Ana").endereco is None
