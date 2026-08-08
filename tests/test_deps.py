"""Testes da cadeia de autenticação de `app.deps` (AUTH-04, AUTH-06, AUTH-08).

`get_claims(request)` lê o evento do Mangum; as demais derivam das claims e são
testadas passando o dict/string diretamente (o mesmo valor que o `Depends` injeta).
"""
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.deps import get_claims, get_clinic_id, get_current_role, require_admin


def _request_com_claims(claims: dict | None) -> Request:
    """Request com o evento do Mangum contendo (ou não) claims do JWT Authorizer."""
    authorizer = {"jwt": {"claims": claims}} if claims is not None else {}
    scope = {
        "type": "http",
        "headers": [],
        "aws.event": {"requestContext": {"authorizer": authorizer}},
    }
    return Request(scope)


# --- get_claims: extração do evento do Mangum ---

def test_get_claims_extrai_do_evento():
    req = _request_com_claims({"custom:clinicId": "clinic-xyz", "custom:role": "admin"})
    assert get_claims(req) == {"custom:clinicId": "clinic-xyz", "custom:role": "admin"}


def test_get_claims_vazio_sem_evento():
    assert get_claims(Request({"type": "http", "headers": []})) == {}


def test_get_claims_vazio_sem_authorizer():
    assert get_claims(_request_com_claims(None)) == {}


# --- get_clinic_id: deriva das claims ---

def test_get_clinic_id_extrai_da_claim():
    assert get_clinic_id({"custom:clinicId": "clinic-xyz"}) == "clinic-xyz"


def test_get_clinic_id_sem_claim_401():
    with pytest.raises(HTTPException) as exc:
        get_clinic_id({})
    assert exc.value.status_code == 401


# --- papéis ---

def test_get_current_role():
    assert get_current_role({"custom:role": "admin"}) == "admin"
    assert get_current_role({}) == ""  # fail-closed


def test_require_admin_permite_admin():
    require_admin("admin")  # não levanta


def test_require_admin_barra_membro():
    with pytest.raises(HTTPException) as exc:
        require_admin("membro")
    assert exc.value.status_code == 403


def test_require_admin_barra_sem_role():
    with pytest.raises(HTTPException) as exc:
        require_admin("")
    assert exc.value.status_code == 403
