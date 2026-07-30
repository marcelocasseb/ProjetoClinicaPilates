#!/usr/bin/env python
"""Onboarding de clínica nova: cria a clínica + o 1º admin (AUTH-01 / AD-012, D1).

Roda **na máquina do dono** com credencial AWS admin (boto3). Gera um `clinicId`
novo, cria o admin no Cognito (AdminCreateUser, e-mail suprimido) e imprime o
clinicId + a senha temporária para repasse fora de banda. Nada disso fica exposto
na web — o nascimento de uma clínica só acontece por este comando.

Uso:
    python scripts/criar_clinica.py --email dono@zen.com --clinica "Clínica Zen" \
        --user-pool-id us-east-1_XXXX

Descubra o --user-pool-id no output da stack:
    aws cloudformation describe-stacks --stack-name clinica-pilates \
        --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text
"""
import argparse
import sys
from pathlib import Path

import boto3

# Permite rodar direto (python scripts/criar_clinica.py) achando o pacote em src/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.cognito_admin import EmailJaExiste, criar_clinica_com_admin  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cria uma clínica nova e seu primeiro admin no Cognito."
    )
    parser.add_argument("--email", required=True, help="E-mail do admin da clínica.")
    parser.add_argument(
        "--clinica", required=True, help="Nome da clínica (só para exibição/log)."
    )
    parser.add_argument(
        "--user-pool-id", required=True, help="ID do Cognito User Pool (output da stack)."
    )
    parser.add_argument(
        "--clinic-id",
        default=None,
        help="Opcional: usa este clinicId em vez de gerar um novo (ex.: 'clinica-zen' "
        "para o admin herdar os dados de demo já semeados). Por padrão, gera um novo.",
    )
    parser.add_argument(
        "--email-invite",
        action="store_true",
        help="Envia a senha temporária por e-mail (convite do Cognito). Sem esta flag, "
        "o e-mail é suprimido e a senha é só impressa aqui para repasse manual.",
    )
    args = parser.parse_args()

    # A região vai embutida no pool id (ex.: "us-east-1_ABC") — usa ela no cliente
    # para não depender do default region da AWS local do operador.
    regiao = args.user_pool_id.split("_")[0]
    cognito = boto3.client("cognito-idp", region_name=regiao)

    try:
        res = criar_clinica_com_admin(
            args.email,
            user_pool_id=args.user_pool_id,
            client=cognito,
            clinic_id=args.clinic_id,
            enviar_email=args.email_invite,
        )
    except EmailJaExiste as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print("Clínica criada com sucesso.")
    print(f"  Clínica:          {args.clinica}")
    print(f"  clinicId:         {res['clinic_id']}")
    print(f"  Admin (e-mail):   {res['email']}")
    print(f"  Senha temporária: {res['senha_temporaria']}")
    print()
    if args.email_invite:
        print("Convite enviado por e-mail (peça para olhar o spam). A senha acima fica")
        print("como backup. No 1º login o Cognito exige a troca da senha.")
    else:
        print("Repasse a senha ao admin fora de banda. No 1º login o Cognito exige a troca.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
