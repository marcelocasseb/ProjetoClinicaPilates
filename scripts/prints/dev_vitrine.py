"""Backend local para os prints do site: o dev_local.py do projeto + mais dados de exemplo.

Uso (na raiz do projeto):
    .venv\\Scripts\\python scripts\\prints\\dev_vitrine.py

Veja scripts/prints/README.md.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import dev_local  # noqa: E402  (configura env falso antes do boto3)
from fastapi.testclient import TestClient  # noqa: E402

_popular_original = dev_local.popular


def popular(app):
    _popular_original(app)
    from app.repository_clinica import ClinicaRepository

    ClinicaRepository().set_nome(dev_local.CLINICA, "Studio Equilíbrio Pilates")
    c = TestClient(app)

    def ok(r):
        if r.status_code >= 300:
            raise RuntimeError(f"{r.request.method} {r.request.url}: {r.text}")
        return r.json()

    for nome, cat in [("Reformer", "Grande porte"), ("Cadillac", "Grande porte"),
                      ("Chair", "Médio porte"), ("Barrel", "Médio porte"),
                      ("Bola suíça", "Acessório"), ("Faixa elástica", "Acessório")]:
        ok(c.post("/aparelhos", json={"nome": nome, "categoria": cat}))

    for t in ("Footwork", "Alongamento", "Fortalecimento", "Mobilidade", "Equilíbrio",
              "Respiração", "Core"):
        c.post("/tipos-treino", json={"nome": t})  # alguns já vêm de fábrica: ignora repetidos

    pacientes = ok(c.get("/pacientes"))
    pacientes = pacientes.get("items", pacientes) if isinstance(pacientes, dict) else pacientes
    profs = ok(c.get("/profissionais"))
    profs = profs.get("items", profs) if isinstance(profs, dict) else profs
    ana = next(p for p in profs if p["nome"].startswith("Dra. Ana"))
    hoje = date.today()
    for p in pacientes[:4]:
        for i, aps in enumerate([
            [("Reformer", ["Footwork", "Alongamento"]), ("Chair", ["Fortalecimento"])],
            [("Cadillac", ["Mobilidade"]), ("Bola suíça", ["Equilíbrio"])],
            [("Reformer", ["Fortalecimento"]), ("Barrel", ["Alongamento"])],
        ]):
            ok(c.post(f"/pacientes/{p['id']}/sessoes", json={
                "data": (hoje - timedelta(days=7 * i + 2)).isoformat(),
                "profissionalId": ana["id"], "profissional": ana["nome"],
                "observacao": "Boa evolução na mobilidade da coluna." if i == 0 else None,
                "aparelhos": [{"nome": n, "treinos": t} for n, t in aps],
            }))
    # Segunda (dia 1) cheia na escala. O navegador dos prints finge ser a próxima segunda às
    # 08:15 (mesma conta em telas.js e aula_fotos.js).
    por_nome = {p["nome"]: p["id"] for p in pacientes}
    for n, hora in [("João Pedro Costa", "07:00"), ("Fernanda Rocha", "08:00"),
                    ("Patrícia Souza", "08:00"), ("Lucas Oliveira", "09:00"),
                    ("Rebecca Lima", "17:00"), ("João Pedro Costa", "18:00"),
                    ("Fernanda Rocha", "19:00"), ("Patrícia Souza", "19:00")]:
        r = c.post("/escala", json={"dia": 1, "hora": hora, "pacienteId": por_nome[n]})
        if r.status_code >= 300:
            print("escala:", r.text)
    segunda = hoje + timedelta(days=(7 - hoje.weekday()) % 7)  # hoje, se já for segunda
    seg = segunda.isoformat()
    paulo = next(p for p in profs if p["nome"].startswith("Dr. Paulo"))
    for hora, q in [("09:00", {"pacienteId": por_nome["Lucas Oliveira"], "profissionalId": ana["id"]}),
                    ("09:00", {"nome": "Camila Ferreira", "telefone": "(91) 99000-3333"}),
                    ("17:00", {"pacienteId": por_nome["Rebecca Lima"], "profissionalId": paulo["id"]}),
                    ("18:00", {"pacienteId": por_nome["João Pedro Costa"], "profissionalId": paulo["id"]})]:
        ok(c.post("/agenda", json={"data": seg, "hora": hora, **q}))
    # Uma mensalidade vencendo na segunda e uma atrasada (vencida no dia anterior)
    ok(c.put(f"/financeiro/planos/{por_nome['Beatriz Santos']}",
             json={"valorCentavos": 32000, "diaVencimento": segunda.day, "frequencia": 2}))
    ok(c.put(f"/financeiro/planos/{por_nome['Carlos Mendes']}",
             json={"valorCentavos": 32000, "diaVencimento": max(1, segunda.day - 1), "frequencia": 2}))

    ok(c.post(f"/pacientes/{pacientes[0]['id']}/avaliacoes", json={
        "data": (hoje - timedelta(days=30)).isoformat(),
        "queixaPrincipal": "Dor lombar ao final do dia",
        "diagnosticoMedico": "Lombalgia mecânica",
        "pressaoArterial": "12/8", "fc": "72",
        "medidas": {"abdomen": "82", "coxa": "54"},
    }))


dev_local.popular = popular

if __name__ == "__main__":
    dev_local.main()
