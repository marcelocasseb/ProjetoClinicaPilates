"""Provisionamento de usuários no Cognito (AD-012 / AUTH-01, AUTH-07).

Camada fina sobre `AdminCreateUser`. É o **único** lugar onde uma conta nasce —
compartilhado pelo script CLI de onboarding (`scripts/criar_clinica.py`, cria o
1º admin de uma clínica nova) e pelo endpoint `POST /membros` (admin cria a equipe).

Regras (AD-012):
- a conta nasce com `custom:clinicId` e `custom:role` **carimbados pelo servidor**
  (nunca escolhidos pelo usuário);
- e-mail já verificado + `MessageAction=SUPPRESS` (Cognito não manda e-mail — a
  senha temporária é devolvida a quem chamou, para repasse fora de banda, D2);
- no 1º login o Cognito força a troca da senha temporária (NEW_PASSWORD_REQUIRED).
"""
from __future__ import annotations

import secrets
import string
import uuid
from typing import Optional

import boto3

ROLE_ADMIN = "admin"
ROLE_MEMBRO = "membro"


class EmailJaExiste(Exception):
    """E-mail já cadastrado no User Pool (não duplica usuário)."""


def gerar_clinic_id() -> str:
    """Gera um `clinicId` novo e opaco. Único ponto onde uma clínica nasce (AD-012)."""
    return f"clinic-{uuid.uuid4().hex[:12]}"


def _gerar_senha_temporaria() -> str:
    """Senha temporária que satisfaz a policy do pool (maiúscula, minúscula, dígito, ≥8)."""
    alfabeto = string.ascii_letters + string.digits
    corpo = "".join(secrets.choice(alfabeto) for _ in range(12))
    # Garante ao menos 1 de cada classe exigida pela PasswordPolicy do template.
    return f"A{corpo}a9"


def criar_usuario(
    email: str,
    clinic_id: str,
    role: str,
    *,
    user_pool_id: str,
    client=None,
) -> dict:
    """Cria um usuário carimbando clínica e papel; devolve `{email, senha_temporaria}`.

    `client` permite injetar um cliente boto3 (testes com moto). Levanta
    `EmailJaExiste` se o e-mail já estiver no pool.
    """
    cognito = client or boto3.client("cognito-idp")
    senha = _gerar_senha_temporaria()
    try:
        cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            TemporaryPassword=senha,
            MessageAction="SUPPRESS",
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "custom:clinicId", "Value": clinic_id},
                {"Name": "custom:role", "Value": role},
            ],
        )
    except cognito.exceptions.UsernameExistsException as exc:
        raise EmailJaExiste(f"O e-mail {email} já está cadastrado.") from exc

    return {"email": email, "senha_temporaria": senha}


def criar_clinica_com_admin(
    email: str,
    *,
    user_pool_id: str,
    client=None,
    clinic_id: Optional[str] = None,
) -> dict:
    """Onboarding de clínica nova: gera o clinicId e cria o 1º admin (role=admin).

    Devolve `{clinic_id, email, senha_temporaria}`. Se o e-mail já existe, propaga
    `EmailJaExiste` **antes** de qualquer efeito — não deixa clinicId órfão (o id só
    é "usado" ao criar o usuário; se falhar, nada persiste).
    """
    novo_clinic_id = clinic_id or gerar_clinic_id()
    res = criar_usuario(
        email,
        novo_clinic_id,
        ROLE_ADMIN,
        user_pool_id=user_pool_id,
        client=client,
    )
    return {"clinic_id": novo_clinic_id, **res}
