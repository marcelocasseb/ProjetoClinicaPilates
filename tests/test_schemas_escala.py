"""Testes dos schemas Pydantic da Escala Semanal (ESC-03, ESC-07)."""
import pytest
from pydantic import ValidationError

from app.schemas_escala import EscalaCreate, EscalaOut


def _payload(**kw):
    base = {"dia": 1, "hora": "07:00", "pacienteId": "p1"}
    base.update(kw)
    return base


def test_matricula_valida():
    m = EscalaCreate(**_payload())
    assert m.dia == 1
    assert m.hora == "07:00"
    assert m.pacienteId == "p1"


@pytest.mark.parametrize("dia", [1, 7])
def test_extremos_do_dia_aceitos(dia):
    assert EscalaCreate(**_payload(dia=dia)).dia == dia


@pytest.mark.parametrize("dia", [0, 8, -1, "segunda", None])
def test_dia_fora_do_intervalo_rejeitado(dia):
    with pytest.raises(ValidationError):
        EscalaCreate(**_payload(dia=dia))


def test_dia_como_string_numerica_aceito():
    """O path param do DELETE chega como string — vira int sem reclamar."""
    assert EscalaCreate(**_payload(dia="3")).dia == 3


@pytest.mark.parametrize("hora", ["06:00", "07:30", "23:59", "00:00"])
def test_horas_validas_aceitas(hora):
    assert EscalaCreate(**_payload(hora=hora)).hora == hora


@pytest.mark.parametrize("hora", ["7:00", "25:00", "07:60", "0700", "07h00", "", "  ", None, 700])
def test_horas_invalidas_rejeitadas(hora):
    """`7:00` também é inválido: sem o zero, o SK sairia da ordem cronológica."""
    with pytest.raises(ValidationError):
        EscalaCreate(**_payload(hora=hora))


def test_hora_com_espacos_e_trimada():
    assert EscalaCreate(**_payload(hora="  08:00  ")).hora == "08:00"


@pytest.mark.parametrize("paciente", ["", "   ", None, 123])
def test_paciente_id_obrigatorio(paciente):
    with pytest.raises(ValidationError):
        EscalaCreate(**_payload(pacienteId=paciente))


def test_paciente_id_trimado():
    assert EscalaCreate(**_payload(pacienteId="  p1  ")).pacienteId == "p1"


def test_campos_desconhecidos_ignorados():
    m = EscalaCreate(**_payload(), profissional="Nat", capacidade=5)
    assert not hasattr(m, "profissional")
    assert not hasattr(m, "capacidade")


def test_saida_carrega_nome_resolvido():
    out = EscalaOut(
        dia=2, hora="19:00", pacienteId="p1", nome="Rebecca", criadoEm="2026-08-28T10:00:00+00:00"
    )
    assert out.nome == "Rebecca"
    assert out.criadoEm.startswith("2026-08-28")


def test_saida_sem_criado_em():
    assert EscalaOut(dia=2, hora="19:00", pacienteId="p1", nome="Rebecca").criadoEm is None
