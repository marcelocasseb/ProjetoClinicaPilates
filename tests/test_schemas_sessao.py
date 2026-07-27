"""Testes dos schemas Pydantic de Sessão/Aula (SES-03, SES-10)."""
import pytest
from pydantic import ValidationError

from app.schemas_sessao import AparelhoSessao, SessaoCreate, SessaoOut, SessaoUpdate


def _aparelho(**kw):
    base = {"aparelhoId": "a1", "nome": "Reformer", "treinos": ["Força"]}
    base.update(kw)
    return base


def test_cria_aula_valida():
    s = SessaoCreate(aparelhos=[_aparelho()])
    assert s.data is None
    assert len(s.aparelhos) == 1
    assert s.aparelhos[0].nome == "Reformer"
    assert s.aparelhos[0].treinos == ["Força"]


def test_aula_sem_aparelho_rejeitada():
    with pytest.raises(ValidationError):
        SessaoCreate(aparelhos=[])


def test_aula_sem_campo_aparelhos_rejeitada():
    with pytest.raises(ValidationError):
        SessaoCreate()


def test_aparelho_sem_nome_rejeitado():
    with pytest.raises(ValidationError):
        SessaoCreate(aparelhos=[{"aparelhoId": "a1", "treinos": ["Força"]}])


def test_aparelho_nome_so_espacos_rejeitado():
    with pytest.raises(ValidationError):
        SessaoCreate(aparelhos=[_aparelho(nome="   ")])


def test_treinos_vazios_descartados():
    s = SessaoCreate(aparelhos=[_aparelho(treinos=["Força", "  ", "", "Mobilidade"])])
    assert s.aparelhos[0].treinos == ["Força", "Mobilidade"]


def test_treinos_ausentes_viram_lista_vazia():
    a = AparelhoSessao(nome="Cadillac")
    assert a.treinos == []
    a2 = AparelhoSessao(nome="Cadillac", treinos=None)
    assert a2.treinos == []


def test_nome_e_treinos_sao_trimados():
    a = AparelhoSessao(nome="  Reformer ", treinos=[" Força "])
    assert a.nome == "Reformer"
    assert a.treinos == ["Força"]


def test_data_valida_aceita():
    s = SessaoCreate(data="2026-07-27", aparelhos=[_aparelho()])
    assert s.data == "2026-07-27"


def test_data_vazia_vira_none():
    s = SessaoCreate(data="   ", aparelhos=[_aparelho()])
    assert s.data is None


def test_data_invalida_rejeitada():
    with pytest.raises(ValidationError):
        SessaoCreate(data="27/07/2026", aparelhos=[_aparelho()])


def test_profissional_e_observacao_vazios_viram_none():
    s = SessaoCreate(profissional="  ", observacao="", aparelhos=[_aparelho()])
    assert s.profissional is None
    assert s.observacao is None


def test_profissional_e_observacao_preenchidos():
    s = SessaoCreate(
        profissional="  Ana  ", observacao="  aluno evoluindo ", aparelhos=[_aparelho()]
    )
    assert s.profissional == "Ana"
    assert s.observacao == "aluno evoluindo"


def test_campos_desconhecidos_ignorados():
    s = SessaoCreate(aparelhos=[_aparelho()], lixo="y")
    assert not hasattr(s, "lixo")


def test_update_tambem_exige_aparelho():
    with pytest.raises(ValidationError):
        SessaoUpdate(aparelhos=[])


def test_sessao_out_monta():
    out = SessaoOut(
        id="s1",
        pacienteId="p1",
        data="2026-07-27",
        profissional="Ana",
        observacao="ok",
        aparelhos=[_aparelho(treinos=["Força", "Mobilidade"])],
        ativo=True,
        criadoEm="2026-07-27T10:00:00Z",
        atualizadoEm="2026-07-27T10:00:00Z",
    )
    assert out.id == "s1"
    assert out.pacienteId == "p1"
    assert out.aparelhos[0].treinos == ["Força", "Mobilidade"]
