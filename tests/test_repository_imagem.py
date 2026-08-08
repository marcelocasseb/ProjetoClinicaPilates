"""Testes do repositório de imagens (IMG-01..04, IMG-08 — isolamento)."""
from app.repository_imagem import ImagemRepository


def _repo(clinic="c1", paciente="p1"):
    return ImagemRepository(clinic_id=clinic, paciente_id=paciente)


def test_add_get_e_contar(dynamo_table):
    repo = _repo()
    assert repo.list() == []
    assert repo.contar() == 0
    meta = repo.add("img1", "c1/p1/img1.jpg", "image/jpeg")
    assert meta["id"] == "img1"
    assert meta["key"] == "c1/p1/img1.jpg"
    assert meta["contentType"] == "image/jpeg"
    assert "criadoEm" in meta
    assert repo.get("img1")["contentType"] == "image/jpeg"
    assert repo.contar() == 1


def test_list_retorna_todas_do_paciente(dynamo_table):
    repo = _repo()
    repo.add("i1", "c1/p1/i1.jpg", "image/jpeg")
    repo.add("i2", "c1/p1/i2.png", "image/png")
    ids = {i["id"] for i in repo.list()}
    assert ids == {"i1", "i2"}


def test_delete_remove_fisicamente(dynamo_table):
    repo = _repo()
    repo.add("i1", "c1/p1/i1.jpg", "image/jpeg")
    repo.delete("i1")
    assert repo.get("i1") is None
    assert repo.contar() == 0


def test_isolamento_entre_clinicas(dynamo_table):
    _repo(clinic="c1").add("i1", "c1/p1/i1.jpg", "image/jpeg")
    assert _repo(clinic="c2").get("i1") is None
    assert _repo(clinic="c2").list() == []


def test_isolamento_entre_pacientes(dynamo_table):
    _repo(paciente="p1").add("i1", "c1/p1/i1.jpg", "image/jpeg")
    assert _repo(paciente="p2").get("i1") is None
    assert _repo(paciente="p2").list() == []
