"""Testes da padronização de nome, endereço, telefone e e-mail."""
import pytest
from fastapi.testclient import TestClient

from app import normaliza
from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("MARIA DA SILVA", "Maria da Silva"),
        ("  maria   da   silva ", "Maria da Silva"),
        ("joão DOS santos e souza", "João dos Santos e Souza"),
        ("ana-clara d'ávila", "Ana-Clara D'Ávila"),
        ("joão pedro ii", "João Pedro II"),
        ("DA COSTA", "Da Costa"),  # partícula só fica minúscula no meio
        ("rua das flores", "Rua das Flores"),
        ("rodovia BR-316", "Rodovia BR-316"),  # código com número fica como veio
        ("BELÉM", "Belém"),
        # escrito com maiúsculas e minúsculas misturadas é de propósito: respeita
        ("Jardim Shangri-lá", "Jardim Shangri-lá"),
        ("Suzana Del Carmen", "Suzana Del Carmen"),
        ("ronald McDonald", "Ronald McDonald"),
        # sigla curta no meio de nome normal fica; nome todo em maiúsculas não
        ("Maria MT", "Maria MT"),
        ("Priscila  Georges M. Valente", "Priscila Georges M. Valente"),
        ("ANA LUZ", "Ana Luz"),
        ("", ""),
        (None, None),
    ],
)
def test_nome_proprio(entrada, esperado):
    assert normaliza.nome_proprio(entrada) == esperado


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("91981111111", "(91) 98111-1111"),
        ("91 98111 1111", "(91) 98111-1111"),
        ("+55 (91) 98111-1111", "(91) 98111-1111"),
        ("9132221111", "(91) 3222-1111"),
        ("+1 415 555 0100", "+1 415 555 0100"),  # fora do padrão BR: só tira as pontas
        (None, None),
    ],
)
def test_telefone(entrada, esperado):
    assert normaliza.telefone(entrada) == esperado


def test_email_e_espacos():
    assert normaliza.email("  Maria.Silva@Gmail.COM ") == "maria.silva@gmail.com"
    assert normaliza.espacos("  AP   12B ") == "AP 12B"


def test_paciente_gravado_padronizado(dynamo_table):
    body = client.post(
        "/pacientes",
        json={
            "nome": "  MARIA  da SILVA ",
            "telefone": "91981111111",
            "email": " Maria@Gmail.COM ",
            "endereco": {
                "logradouro": "RUA DAS FLORES",
                "numero": " 12 ",
                "complemento": "AP  12B",
                "bairro": "umarizal",
                "cidade": "BELÉM",
                "uf": "pa",
            },
        },
    ).json()
    assert body["nome"] == "Maria da Silva"
    assert body["telefone"] == "(91) 98111-1111"
    assert body["email"] == "maria@gmail.com"
    end = body["endereco"]
    assert end["logradouro"] == "Rua das Flores"
    assert end["numero"] == "12"
    assert end["complemento"] == "AP 12B"
    assert end["bairro"] == "Umarizal"
    assert end["cidade"] == "Belém"
    assert end["uf"] == "PA"


def test_lista_de_pacientes_ordena_sem_depender_de_maiusculas(dynamo_table):
    for n in ("zeca", "ANA", "bruno"):
        client.post("/pacientes", json={"nome": n})
    assert [p["nome"] for p in client.get("/pacientes").json()] == ["Ana", "Bruno", "Zeca"]


def test_agenda_e_profissional_padronizados(dynamo_table):
    ag = client.post(
        "/agenda", json={"data": "2026-10-19", "hora": "07:00", "nome": "JOÃO silva", "telefone": "91981111111"}
    ).json()
    assert ag["nome"] == "João Silva"
    assert ag["telefone"] == "(91) 98111-1111"
    prof = client.post("/profissionais", json={"nome": "dra. ANA lima", "telefone": "9132221111"}).json()
    assert prof["nome"] == "Dra. Ana Lima"
    assert prof["telefone"] == "(91) 3222-1111"
