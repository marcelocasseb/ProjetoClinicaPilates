"""Backend LOCAL para testar o front com dados, sem AWS e sem Docker.

Sobe a API em http://localhost:8000 com o DynamoDB e o S3 simulados em memória (moto,
o mesmo dos testes) e já preenchidos com uma clínica de exemplo: pacientes, escala,
agenda da semana (com gente sem cadastro e aula paga), preços, planos e caixa.

Uso (na raiz do projeto):
    .venv\\Scripts\\python scripts\\dev_local.py            # como admin
    .venv\\Scripts\\python scripts\\dev_local.py --membro   # como membro (sem Financeiro)

E o front, em outro terminal:
    cd frontend; npm run dev:local

O login do front continua no Cognito de verdade (entre com sua conta normal), mas este
backend IGNORA o token: todo pedido é atendido como a clínica "local". Nada aqui toca a
AWS, e os dados somem ao fechar (Ctrl+C) — cada execução recomeça do zero.

Limitação: upload de imagens não funciona (a URL assinada do S3 simulado não é
alcançável pelo navegador).
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# Credenciais falsas ANTES de qualquer boto3: garante que nada vá para a AWS real.
os.environ.update(
    TABLE_NAME="clinica-local",
    IMAGES_BUCKET="clinica-local-imgs",
    AWS_DEFAULT_REGION="us-east-1",
    AWS_ACCESS_KEY_ID="local",
    AWS_SECRET_ACCESS_KEY="local",
)
os.environ.pop("AWS_PROFILE", None)

import boto3  # noqa: E402
import uvicorn  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from moto import mock_aws  # noqa: E402

CLINICA = "local"
PORTA = 8000


def criar_tabela():
    boto3.resource("dynamodb").create_table(
        TableName=os.environ["TABLE_NAME"],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": n, "AttributeType": "S"} for n in ("PK", "SK", "GSI1PK", "GSI1SK")
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
    boto3.client("s3").create_bucket(Bucket=os.environ["IMAGES_BUCKET"])


def popular(app):
    """Dados de exemplo, gravados pela própria API (passam pelas mesmas validações)."""
    from app.repository_clinica import ClinicaRepository

    ClinicaRepository().set_nome(CLINICA, "Clínica Local (teste)")
    c = TestClient(app)

    def ok(resp):
        if resp.status_code >= 300:
            raise RuntimeError(f"{resp.request.method} {resp.request.url}: {resp.text}")
        return resp.json()

    nomes = [
        ("Beatriz Santos", "(91) 98111-1111"),
        ("Carlos Mendes", "(91) 98222-2222"),
        ("Mariana Alves", "(91) 98333-3333"),
        ("Rebecca Lima", "(91) 98444-4444"),
        ("João Pedro Costa", "(91) 98555-5555"),
        ("Fernanda Rocha", "(91) 98666-6666"),
        ("Lucas Oliveira", None),
        ("Patrícia Souza", "(91) 98777-7777"),
    ]
    ids = {
        n: ok(c.post("/pacientes", json={"nome": n, "telefone": t or ""}))["id"] for n, t in nomes
    }

    # Escala fixa da semana
    grade = [
        ("Beatriz Santos", 1, "06:00"), ("Carlos Mendes", 1, "06:00"), ("Mariana Alves", 1, "07:00"),
        ("Beatriz Santos", 3, "06:00"), ("Carlos Mendes", 3, "06:00"), ("Rebecca Lima", 2, "18:00"),
        ("Fernanda Rocha", 2, "18:00"), ("Rebecca Lima", 4, "18:00"), ("Lucas Oliveira", 5, "08:00"),
        ("Patrícia Souza", 5, "08:00"), ("João Pedro Costa", 6, "09:00"),
    ]
    for n, dia, hora in grade:
        ok(c.post("/escala", json={"dia": dia, "hora": hora, "pacienteId": ids[n]}))

    # Preços, planos e caixa (alguns devendo a mensalidade do mês)
    ok(c.put("/financeiro/config", json={"aulaAvulsaCentavos": 8000, "reposicaoCentavos": 5000}))
    for n in ("Beatriz Santos", "Carlos Mendes", "Mariana Alves", "Rebecca Lima"):
        ok(c.put(f"/financeiro/planos/{ids[n]}",
                 json={"valorCentavos": 32000, "diaVencimento": 10, "frequencia": 2}))
    hoje = date.today()
    mes = hoje.strftime("%Y-%m")
    for n in ("Mariana Alves", "Rebecca Lima"):
        ok(c.post("/financeiro/lancamentos", json={
            "tipo": "entrada", "data": hoje.isoformat(), "valorCentavos": 32000,
            "descricao": f"Mensalidade — {n}", "formaPagamento": "pix",
            "pacienteId": ids[n], "competencia": mes}))
    ok(c.post("/financeiro/lancamentos", json={
        "tipo": "saida", "data": hoje.isoformat(), "valorCentavos": 15000,
        "descricao": "Conta de luz", "formaPagamento": "pix"}))

    # Agenda: semana atual, com cadastrados, pessoas novas e um agendamento já pago
    segunda = hoje - timedelta(days=hoje.weekday())

    def dia(n):
        return (segunda + timedelta(days=n)).isoformat()

    profs = {
        n: ok(c.post("/profissionais", json={"nome": n, "telefone": t}))["id"]
        for n, t in [("Dra. Ana Lima", "(91) 98000-0001"), ("Dr. Paulo Reis", ""), ("Carla Nunes", "")]
    }
    ana, paulo = profs["Dra. Ana Lima"], profs["Dr. Paulo Reis"]
    amanha = (hoje + timedelta(days=1)).isoformat()

    marcacoes = [
        (dia(0), "07:00", {"pacienteId": ids["João Pedro Costa"], "profissionalId": ana}),
        (dia(0), "07:00", {"nome": "Ana Clara", "telefone": "(91) 99000-1111", "profissionalId": paulo}),
        (dia(1), "18:00", {"pacienteId": ids["Beatriz Santos"], "profissionalId": ana}),
        (dia(2), "09:00", {"nome": "Roberto Dias", "telefone": "(91) 99000-2222"}),
        (dia(3), "18:00", {"pacienteId": ids["Carlos Mendes"], "profissionalId": paulo}),
        (hoje.isoformat(), "10:00", {"pacienteId": ids["Fernanda Rocha"], "profissionalId": ana}),
        (hoje.isoformat(), "10:00", {"nome": "Juliana Martins", "profissionalId": paulo}),
        (hoje.isoformat(), "17:00", {"pacienteId": ids["Lucas Oliveira"]}),
        (amanha, "06:00", {"pacienteId": ids["Beatriz Santos"], "profissionalId": ana}),
        (amanha, "06:00", {"pacienteId": ids["Mariana Alves"], "profissionalId": paulo}),
        (dia(7), "08:00", {"pacienteId": ids["Patrícia Souza"]}),
    ]
    criados = [ok(c.post("/agenda", json={"data": d, "hora": h, **q})) for d, h, q in marcacoes]
    paga = criados[5]  # Fernanda, hoje 10:00
    ok(c.post(f"/agenda/{paga['data']}/{paga['hora']}/{paga['id']}/pagamento", json={
        "valorCentavos": 5000, "formaPagamento": "dinheiro",
        "dataPagamento": hoje.isoformat()}))


def main():
    papel = "membro" if "--membro" in sys.argv else "admin"

    with mock_aws():
        criar_tabela()

        from app.deps import get_claims
        from app.main import app

        # O token do front é ignorado: toda chamada vira a clínica "local".
        app.dependency_overrides[get_claims] = lambda: {
            "custom:clinicId": CLINICA,
            "custom:role": "admin",  # popular sempre como admin
            "email": "teste@local",
        }
        # Em produção o CORS é do API Gateway; aqui o front (5173) chama direto.
        # Tem que vir ANTES do popular: depois que o app atende o 1º pedido, o
        # Starlette não aceita mais middleware.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        popular(app)
        app.dependency_overrides[get_claims] = lambda: {
            "custom:clinicId": CLINICA,
            "custom:role": papel,
            "email": "teste@local",
        }

        print(f"\n  Backend local em http://localhost:{PORTA}  (papel: {papel})")
        print("  Front: cd frontend; npm run dev:local   |   Ctrl+C encerra (dados somem)\n")
        uvicorn.run(app, host="127.0.0.1", port=PORTA, log_level="warning")


if __name__ == "__main__":
    main()
