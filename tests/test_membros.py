"""Testes do endpoint de provisionamento de membros (AUTH-07, AUTH-08)."""
import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app import cognito_admin
from app.deps import get_claims, get_clinic_id
from app.main import app
from app.repository_clinica import ClinicaRepository

client = TestClient(app)

ADMIN = {"custom:clinicId": "clinica-a", "custom:role": "admin"}
MEMBRO = {"custom:clinicId": "clinica-a", "custom:role": "membro"}


@pytest.fixture
def cognito_pool(dynamo_table, monkeypatch):
    """User Pool moto + USER_POOL_ID no ambiente (como o Lambda recebe do template).

    Depende de `dynamo_table`: o endpoint também registra o membro no DynamoDB.
    """
    with mock_aws():
        cognito = boto3.client("cognito-idp", region_name="us-east-1")
        pool = cognito.create_user_pool(
            PoolName="test",
            UsernameAttributes=["email"],
            Schema=[
                {"Name": "clinicId", "AttributeDataType": "String", "Mutable": True},
                {"Name": "role", "AttributeDataType": "String", "Mutable": True},
            ],
        )
        pool_id = pool["UserPool"]["Id"]
        monkeypatch.setenv("USER_POOL_ID", pool_id)
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        yield cognito, pool_id


@pytest.fixture
def as_user():
    """Simula o usuário logado sobrescrevendo as claims (raiz da cadeia de auth).

    Remove o override de header do conftest para que `get_clinic_id` derive das
    claims injetadas (é o que valida que o clinicId vem do token, não do corpo).
    """
    def _set(claims):
        app.dependency_overrides.pop(get_clinic_id, None)
        app.dependency_overrides[get_claims] = lambda: claims

    yield _set
    app.dependency_overrides.pop(get_claims, None)


def _atributos(cognito, pool_id, email):
    user = cognito.admin_get_user(UserPoolId=pool_id, Username=email)
    return {a["Name"]: a["Value"] for a in user["UserAttributes"]}


def test_admin_cria_membro_201(cognito_pool, as_user):
    cognito, pool_id = cognito_pool
    as_user(ADMIN)

    resp = client.post("/membros", json={"nome": "  Bia   Lima ", "email": "novo@zen.com"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "novo@zen.com"
    assert body["senha_temporaria"]
    assert body["nome"] == "Bia Lima"                 # espaços normalizados

    attrs = _atributos(cognito, pool_id, "novo@zen.com")
    assert attrs["custom:clinicId"] == "clinica-a"   # herdado do token do admin
    assert attrs["custom:role"] == "membro"
    assert attrs["name"] == "Bia Lima"               # chega no idToken

    # Registrado no banco da clínica do admin (e só nela).
    membros = ClinicaRepository().list_membros("clinica-a")
    assert [(m["email"], m["nome"], m["role"]) for m in membros] == [
        ("novo@zen.com", "Bia Lima", "membro")
    ]
    assert ClinicaRepository().list_membros("clinica-b") == []


def test_membro_nao_pode_criar_membro_403(cognito_pool, as_user):
    as_user(MEMBRO)
    resp = client.post("/membros", json={"nome": "X", "email": "x@zen.com"})
    assert resp.status_code == 403


def test_sem_role_403(cognito_pool, as_user):
    as_user({"custom:clinicId": "clinica-a"})  # sem custom:role → fail-closed
    resp = client.post("/membros", json={"nome": "X", "email": "x@zen.com"})
    assert resp.status_code == 403


def test_clinicid_e_role_do_corpo_sao_ignorados(cognito_pool, as_user):
    cognito, pool_id = cognito_pool
    as_user(ADMIN)

    # Admin da clinica-a tenta forjar outra clínica/role no corpo — deve ser ignorado.
    resp = client.post(
        "/membros",
        json={"nome": "Forja", "email": "forja@zen.com", "clinicId": "clinica-b", "role": "admin"},
    )

    assert resp.status_code == 201
    attrs = _atributos(cognito, pool_id, "forja@zen.com")
    assert attrs["custom:clinicId"] == "clinica-a"   # do token, não do corpo
    assert attrs["custom:role"] == "membro"          # sempre membro por este endpoint


def test_email_duplicado_409(cognito_pool, as_user):
    as_user(ADMIN)
    client.post("/membros", json={"nome": "Dup", "email": "dup@zen.com"})
    resp = client.post("/membros", json={"nome": "Dup", "email": "dup@zen.com"})
    assert resp.status_code == 409


def test_email_invalido_400(cognito_pool, as_user):
    as_user(ADMIN)
    resp = client.post("/membros", json={"nome": "X", "email": "sem-arroba"})
    assert resp.status_code == 400


def test_nome_obrigatorio_400(cognito_pool, as_user):
    as_user(ADMIN)
    assert client.post("/membros", json={"email": "a@zen.com"}).status_code == 400
    assert client.post("/membros", json={"nome": "   ", "email": "a@zen.com"}).status_code == 400


def test_nome_longo_demais_400(cognito_pool, as_user):
    as_user(ADMIN)
    resp = client.post("/membros", json={"nome": "A" * 81, "email": "a@zen.com"})
    assert resp.status_code == 400


def test_email_duplicado_nao_grava_no_banco(cognito_pool, as_user):
    as_user(ADMIN)
    client.post("/membros", json={"nome": "Primeiro", "email": "dup@zen.com"})
    client.post("/membros", json={"nome": "Segundo", "email": "dup@zen.com"})

    membros = ClinicaRepository().list_membros("clinica-a")
    assert [m["nome"] for m in membros] == ["Primeiro"]   # o 409 não sobrescreve
