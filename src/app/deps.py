"""Dependências compartilhadas entre os routers.

`get_clinic_id` resolve a clínica do solicitante (multi-tenant, AD-007) a partir da
**identidade autenticada**: o JWT Authorizer do API Gateway valida o token Cognito na
borda e injeta as claims no evento; o Mangum as expõe em `scope["aws.event"]`
(API GW v2.0), de onde `get_claims` as lê. O isolamento passa a estar ancorado no
token (não mais num header forjável) — AD-012 / AUTH-04.

Nos testes não há authorizer; o `conftest` instala um `dependency_overrides` que
reproduz o comportamento antigo de header, mantendo a suíte intacta.
"""
from fastapi import Depends, HTTPException, Request, status

CLAIM_CLINIC_ID = "custom:clinicId"
CLAIM_ROLE = "custom:role"
ROLE_ADMIN = "admin"


def get_claims(request: Request) -> dict:
    """Claims do token, injetadas pelo JWT Authorizer (via Mangum). `{}` se ausente.

    É a raiz da cadeia de dependências de autenticação — `get_clinic_id`,
    `get_current_role` e `require_admin` derivam daqui. Nos testes basta sobrescrever
    esta dependência para simular um usuário logado.
    """
    event = request.scope.get("aws.event", {}) or {}
    authorizer = event.get("requestContext", {}).get("authorizer", {}) or {}
    return authorizer.get("jwt", {}).get("claims", {}) or {}


def get_clinic_id(claims: dict = Depends(get_claims)) -> str:
    """`clinicId` da claim do token. Sem clínica → 401 (nunca cai num default)."""
    clinic_id = claims.get(CLAIM_CLINIC_ID)
    if not clinic_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    return clinic_id


def get_current_role(claims: dict = Depends(get_claims)) -> str:
    """Papel do usuário (`admin`|`membro`). Ausente → string vazia (fail-closed)."""
    return claims.get(CLAIM_ROLE, "")


def require_admin(role: str = Depends(get_current_role)) -> None:
    """Barra quem não é admin (403). Usado no provisionamento de membros (AUTH-08)."""
    if role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação.",
        )
