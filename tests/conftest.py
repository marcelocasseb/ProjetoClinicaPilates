"""Fixtures compartilhadas de teste.

`dynamo_table` sobe uma tabela DynamoDB única em memória (moto), espelhando o
schema PK/SK on-demand provisionado pelo template SAM, e aponta `TABLE_NAME`
para ela. Usada pelos testes de repositório e de endpoints de pacientes.
"""
import boto3
import pytest
from fastapi import Header
from moto import mock_aws

TABLE_NAME = "clinica-test-table"


@pytest.fixture(autouse=True)
def clinic_via_header():
    """Reproduz, nos testes, a fonte antiga do clinicId (header `X-Clinic-Id`).

    Em produção `get_clinic_id` lê a claim do token (injetada pelo JWT Authorizer,
    inexistente nos testes). Este override deixa a suíte inteira passar o clinicId
    por header como antes — sem tocar em nenhum teste existente (AUTH-04).
    """
    from app.deps import get_clinic_id
    from app.main import app

    def _via_header(x_clinic_id: str = Header(default=None)) -> str:
        return x_clinic_id or "default"

    app.dependency_overrides[get_clinic_id] = _via_header
    yield
    app.dependency_overrides.pop(get_clinic_id, None)


@pytest.fixture
def dynamo_table(monkeypatch):
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        boto3.resource("dynamodb", region_name="us-east-1").create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield TABLE_NAME
