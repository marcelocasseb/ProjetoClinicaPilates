"""Testes do provisionamento de usuários no Cognito (AUTH-01)."""
import boto3
import pytest
from moto import mock_aws

from app import cognito_admin


def _criar_pool(cognito) -> tuple[str, str]:
    """Cria um User Pool + client espelhando o schema custom do template.yaml."""
    pool = cognito.create_user_pool(
        PoolName="test-pool",
        UsernameAttributes=["email"],
        AdminCreateUserConfig={"AllowAdminCreateUserOnly": True},
        Schema=[
            {"Name": "clinicId", "AttributeDataType": "String", "Mutable": True},
            {"Name": "role", "AttributeDataType": "String", "Mutable": True},
        ],
    )
    pool_id = pool["UserPool"]["Id"]
    return pool_id


def _atributos(cognito, pool_id, email) -> dict:
    user = cognito.admin_get_user(UserPoolId=pool_id, Username=email)
    return {a["Name"]: a["Value"] for a in user["UserAttributes"]}


@mock_aws
def test_criar_clinica_com_admin_carimba_clinicid_e_role():
    cognito = boto3.client("cognito-idp", region_name="us-east-1")
    pool_id = _criar_pool(cognito)

    res = cognito_admin.criar_clinica_com_admin(
        "dono@zen.com", user_pool_id=pool_id, client=cognito
    )

    assert res["clinic_id"].startswith("clinic-")
    assert res["email"] == "dono@zen.com"
    assert res["senha_temporaria"]

    attrs = _atributos(cognito, pool_id, "dono@zen.com")
    assert attrs["custom:clinicId"] == res["clinic_id"]
    assert attrs["custom:role"] == cognito_admin.ROLE_ADMIN


@mock_aws
def test_criar_usuario_membro_usa_clinicid_dado():
    cognito = boto3.client("cognito-idp", region_name="us-east-1")
    pool_id = _criar_pool(cognito)

    res = cognito_admin.criar_usuario(
        "membro@zen.com",
        "clinic-abc",
        cognito_admin.ROLE_MEMBRO,
        user_pool_id=pool_id,
        client=cognito,
    )

    assert res["email"] == "membro@zen.com"
    attrs = _atributos(cognito, pool_id, "membro@zen.com")
    assert attrs["custom:clinicId"] == "clinic-abc"
    assert attrs["custom:role"] == cognito_admin.ROLE_MEMBRO


@mock_aws
def test_email_duplicado_levanta_erro_claro():
    cognito = boto3.client("cognito-idp", region_name="us-east-1")
    pool_id = _criar_pool(cognito)

    cognito_admin.criar_usuario(
        "dup@zen.com", "clinic-x", cognito_admin.ROLE_MEMBRO,
        user_pool_id=pool_id, client=cognito,
    )

    with pytest.raises(cognito_admin.EmailJaExiste):
        cognito_admin.criar_usuario(
            "dup@zen.com", "clinic-x", cognito_admin.ROLE_MEMBRO,
            user_pool_id=pool_id, client=cognito,
        )


def test_clinic_id_gerado_e_unico():
    ids = {cognito_admin.gerar_clinic_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(i.startswith("clinic-") for i in ids)
