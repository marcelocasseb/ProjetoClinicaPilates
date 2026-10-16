"""Padroniza nomes, telefones, e-mails e endereços JÁ GRAVADOS na tabela.

Os schemas passaram a padronizar a entrada (app/normaliza.py), mas o que foi salvo
antes continua como foi digitado. Este script aplica as mesmas regras aos itens
existentes:
    - pacientes (SK=PROFILE): nome (+ GSI1SK, que ordena a lista), telefone, e-mail
      e endereço (logradouro, bairro, cidade, número, complemento, UF);
    - profissionais (SK=PROFISSIONAL#…): nome e telefone;
    - pessoas sem cadastro na Agenda (SK=AGENDA#…, sem pacienteId): nome e telefone.

Uso (na raiz do projeto, com as credenciais da AWS):
    .venv\\Scripts\\python scripts\\padronizar_dados.py            # SIMULA: só lista
    .venv\\Scripts\\python scripts\\padronizar_dados.py --aplicar  # grava

Cada item é atualizado só nos campos que mudam (update_item), com a condição de que
o item ainda exista — nunca cria nem apaga nada. O backup contínuo (PITR) da tabela
cobre um eventual arrependimento.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import boto3  # noqa: E402

from app import normaliza  # noqa: E402

STACK = "clinica-pilates"


def nome_da_tabela() -> str:
    cf = boto3.client("cloudformation")
    return cf.describe_stack_resource(StackName=STACK, LogicalResourceId="ClinicaTable")[
        "StackResourceDetail"
    ]["PhysicalResourceId"]


def _uf(v):
    return v.strip().upper() if isinstance(v, str) else v


def mudancas(item: dict) -> dict:
    """Campos (de primeiro nível) que mudam neste item: {campo: valor_novo}."""
    sk = item.get("SK", "")
    novos = {}

    def campo(nome, regra):
        atual = item.get(nome)
        if isinstance(atual, str):
            novo = regra(atual)
            if novo != atual:
                novos[nome] = novo

    if sk == "PROFILE":
        campo("nome", normaliza.nome_proprio)
        if "nome" in novos and item.get("GSI1SK") is not None:
            novos["GSI1SK"] = novos["nome"]
        campo("telefone", normaliza.telefone)
        campo("email", normaliza.email)
        end = item.get("endereco")
        if isinstance(end, dict):
            regras = {
                "logradouro": normaliza.nome_proprio,
                "bairro": normaliza.nome_proprio,
                "cidade": normaliza.nome_proprio,
                "numero": normaliza.espacos,
                "complemento": normaliza.espacos,
                "uf": _uf,
            }
            novo_end = {
                k: (regras[k](v) if k in regras and isinstance(v, str) else v) for k, v in end.items()
            }
            if novo_end != end:
                novos["endereco"] = novo_end
    elif sk.startswith("PROFISSIONAL#"):
        campo("nome", normaliza.nome_proprio)
        campo("telefone", normaliza.telefone)
    elif sk.startswith("AGENDA#") and not item.get("pacienteId"):
        campo("nome", normaliza.nome_proprio)
        campo("telefone", normaliza.telefone)
    return novos


def main():
    aplicar = "--aplicar" in sys.argv
    tabela = boto3.resource("dynamodb").Table(nome_da_tabela())

    itens, kwargs = [], {}
    while True:
        resp = tabela.scan(**kwargs)
        itens.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    total = 0
    for item in itens:
        novos = mudancas(item)
        if not novos:
            continue
        total += 1
        tipo = item["SK"].split("#")[0]
        print(f"[{tipo}] {item['PK']}")
        for k, v in novos.items():
            if k == "GSI1SK":
                continue
            antes = item.get(k)
            if k == "endereco":
                for ck in v:
                    if v[ck] != antes.get(ck):
                        print(f"    endereco.{ck}: {antes.get(ck)!r} -> {v[ck]!r}")
            else:
                print(f"    {k}: {antes!r} -> {v!r}")
        if aplicar:
            nomes = {f"#{k}": k for k in novos}
            valores = {f":{k}": v for k, v in novos.items()}
            tabela.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET " + ", ".join(f"#{k} = :{k}" for k in novos),
                ConditionExpression="attribute_exists(PK)",
                ExpressionAttributeNames=nomes,
                ExpressionAttributeValues=valores,
            )

    print()
    print(f"{len(itens)} itens lidos; {total} a padronizar.")
    print("Gravado." if aplicar else "SIMULACAO: nada foi gravado. Rode com --aplicar para gravar.")


if __name__ == "__main__":
    main()
