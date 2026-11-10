#!/usr/bin/env python
"""Preenche uma clínica de DEMONSTRAÇÃO com 6 meses de dados para validar os Relatórios.

Grava pelas mesmas classes de repositório do sistema (mesmas chaves e campos). Cria:
alunos novos (2 deles removidos), planos para quem não tem, aulas registradas, Caixa
(mensalidades, avulsas, despesas), marcações na Agenda dentro da retenção e matrículas
na escala para os alunos novos.

Tudo o que é criado vai para um manifesto (`scripts/demo/<clinica>.json`), e
`--desfazer` apaga exatamente esses itens. Nada que já existia é alterado.

Uso (na raiz, com credencial AWS):
    python scripts/semear_demo_relatorios.py --clinic-id clinica-zen \
        --table-name clinica-pilates-ClinicaTable-8YQAEIFAKZGE
    python scripts/semear_demo_relatorios.py --clinic-id clinica-zen \
        --table-name clinica-pilates-ClinicaTable-8YQAEIFAKZGE --desfazer

NUNCA rodar numa clínica de cliente real.
"""
import argparse
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import boto3  # noqa: E402
from boto3.dynamodb.conditions import Attr, Key  # noqa: E402

from app import repository as rep_pac  # noqa: E402
from app import repository_agenda as rep_ag  # noqa: E402
from app import repository_escala as rep_esc  # noqa: E402
from app import repository_financeiro as rep_fin  # noqa: E402
from app import repository_plano as rep_plano  # noqa: E402
from app import repository_sessao as rep_ses  # noqa: E402

PROTEGIDAS = {"clinic-e73061dfafc1", "clinic-4a926fc0dfe7"}  # clientes reais: nunca
NOVOS = ["Aline Prado", "Bruno Teles", "Camila Duarte", "Diego Faria", "Elisa Moura", "Fábio Nunes"]
NOVOS_AGENDA = ["Paula Viana", "Ricardo Gomes", "Sônia Lopes", "Tiago Rocha", "Vera Lúcia"]
FORMAS = ["pix", "pix", "pix", "credito", "debito", "dinheiro", "transferencia"]
HORAS = ["06:00", "07:00", "08:00", "09:00", "17:00", "18:00", "19:00"]


def meses_ate(hoje: date, n: int) -> list[tuple[int, int]]:
    total = hoje.year * 12 + hoje.month - 1
    return [(t // 12, t % 12 + 1) for t in range(total - n + 1, total + 1)]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


class Semeador:
    def __init__(self, clinic: str, tabela: str):
        self.c = clinic
        self.t = tabela
        self.table = boto3.resource("dynamodb", region_name="us-east-1").Table(tabela)
        self.criados: list[dict] = []  # chaves {PK, SK} para o --desfazer
        self.rnd = random.Random(20261109)
        self.hoje = datetime.now(timezone(timedelta(hours=-3))).date()

    def anota(self, pk: str, sk: str):
        self.criados.append({"PK": pk, "SK": sk})

    def _catalogo(self, prefixo: str) -> list[dict]:
        r = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"CLINIC#{self.c}") & Key("SK").begins_with(prefixo),
            FilterExpression=Attr("ativo").eq(True),
        )
        return r.get("Items", [])

    def alunos(self) -> list[dict]:
        """Cria os alunos novos com data de cadastro no passado; 2 deles saem."""
        repo = rep_pac.PacienteRepository(self.c, self.t)
        meses = meses_ate(self.hoje, 6)
        novos = []
        for i, nome in enumerate(NOVOS):
            p = repo.create({"nome": nome, "telefone": f"(15) 9{8100 + i:04d}-{1000 + i * 7:04d}"})
            ano, mes = meses[i]
            criado = datetime(ano, mes, 5 + i, 14, 0, tzinfo=timezone.utc)
            pk = rep_pac._pk(self.c, p["id"])
            self.table.update_item(
                Key={"PK": pk, "SK": "PROFILE"},
                UpdateExpression="SET criadoEm = :c, atualizadoEm = :c",
                ExpressionAttributeValues={":c": iso(criado)},
            )
            self.anota(pk, "PROFILE")
            p["criadoEm"] = iso(criado)
            novos.append(p)
        # Saídas: Bruno sai 2 meses antes do atual, Diego no mês anterior.
        for nome, atras in (("Bruno Teles", 2), ("Diego Faria", 1)):
            p = next(x for x in novos if x["nome"] == nome)
            ano, mes = meses[-1 - atras]
            saida = datetime(ano, mes, 20, 15, 0, tzinfo=timezone.utc)
            self.table.update_item(
                Key={"PK": rep_pac._pk(self.c, p["id"]), "SK": "PROFILE"},
                UpdateExpression="SET ativo = :f, atualizadoEm = :s",
                ExpressionAttributeValues={":f": False, ":s": iso(saida)},
            )
            p["ativo"] = False
            p["removidoEm"] = saida.date()
        return novos

    def planos(self, perfis: list[dict]) -> dict:
        repo = rep_plano.PlanoRepository(self.c, self.t)
        existentes = {p["pacienteId"]: p for p in repo.list_all()}
        tabela = {1: 22000, 2: 32000, 3: 42000}
        for i, p in enumerate(perfis):
            if p["id"] in existentes:
                continue
            freq = (2, 3, 1, 2, 2, 3, 1, 2)[i % 8]
            valor = 0 if i == 3 else tabela[freq]  # um isento
            existentes[p["id"]] = repo.upsert(
                p["id"], {"valorCentavos": valor, "frequencia": freq, "diaVencimento": (5, 10, 15)[i % 3]}
            )
            self.anota(rep_plano._pk(self.c), rep_plano._sk_plano(p["id"]))
        return existentes

    def escala(self, novos: list[dict]):
        repo = rep_esc.EscalaRepository(self.c, self.t)
        for i, p in enumerate(x for x in novos if x.get("ativo", True)):
            for dia in ((1, 3), (2, 4), (3, 5), (1, 5))[i % 4]:
                hora = HORAS[(i * 2 + dia) % len(HORAS)]
                if repo.create(dia, hora, p["id"], p["nome"]):
                    self.anota(rep_esc._pk(self.c), rep_esc._sk(dia, hora, p["id"]))

    def _ativo_em(self, p: dict, d: date) -> bool:
        criado = datetime.fromisoformat(p["criadoEm"]).date()
        if d < criado:
            return False
        return p.get("ativo", True) or d < p.get("removidoEm", date.max)

    def aulas(self, perfis: list[dict], planos: dict, profs: list[dict], aparelhos: list[dict], treinos: list[str]):
        inicio = date(*meses_ate(self.hoje, 6)[0], 1)
        d = inicio
        while d <= self.hoje:
            if d.weekday() < 6:  # segunda a sábado
                for p in perfis:
                    freq = int((planos.get(p["id"]) or {}).get("frequencia") or 2)
                    # chance de aula no dia ≈ frequência semanal / 6 dias, com faltas
                    if not self._ativo_em(p, d) or self.rnd.random() > freq / 6 * 0.85:
                        continue
                    prof = self.rnd.choice(profs) if profs and self.rnd.random() > 0.08 else None
                    escolhidos = self.rnd.sample(aparelhos, k=min(len(aparelhos), self.rnd.choice((1, 2, 2))))
                    s = rep_ses.SessaoRepository(self.c, p["id"], self.t).create(
                        {
                            "data": d.isoformat(),
                            "profissionalId": prof["id"] if prof else None,
                            "profissional": prof["nome"] if prof else None,
                            "aparelhos": [
                                {"aparelhoId": a["id"], "nome": a["nome"],
                                 "treinos": self.rnd.sample(treinos, k=min(len(treinos), self.rnd.choice((1, 2))))}
                                for a in escolhidos
                            ],
                        }
                    )
                    self.anota(rep_ses._pk(self.c, p["id"]), rep_ses._sk(s["id"]))
            d += timedelta(days=1)

    def caixa(self, perfis: list[dict], planos: dict):
        repo = rep_fin.FinanceiroRepository(self.c, self.t)

        def lanca(**campos):
            l = repo.create(campos)
            self.anota(rep_fin._pk(self.c, rep_fin.mes_da_data(campos["data"])), rep_fin._sk(l["id"]))

        for ano, mes in meses_ate(self.hoje, 6):
            atual = (ano, mes) == (self.hoje.year, self.hoje.month)
            competencia = f"{ano}-{mes:02d}"
            for p in perfis:
                plano = planos.get(p["id"])
                valor = int((plano or {}).get("valorCentavos") or 0)
                if not valor or not self._ativo_em(p, date(ano, mes, 28 if not atual else self.hoje.day)):
                    continue
                if atual and self.rnd.random() < 0.45:
                    continue  # mês corrente: parte ainda em aberto
                dia = min(int(plano.get("diaVencimento") or 10) + self.rnd.randint(-3, 4), 28)
                d = date(ano, mes, max(1, dia))
                if d > self.hoje:
                    continue
                parcial = self.rnd.random() < 0.08
                lanca(tipo="entrada", data=d.isoformat(), valorCentavos=valor // 2 if parcial else valor,
                      descricao=f"Mensalidade — {p['nome']}", formaPagamento=self.rnd.choice(FORMAS),
                      pacienteId=p["id"], competencia=competencia)
            dia_avulsa = date(ano, mes, min(18, self.hoje.day if atual else 18))
            lanca(tipo="entrada", data=dia_avulsa.isoformat(), valorCentavos=8000 * self.rnd.randint(2, 6),
                  descricao="Aulas avulsas e experimentais", formaPagamento=self.rnd.choice(FORMAS))
            despesas = [("Aluguel da sala", 180000, 5), ("Conta de luz", 21000 + self.rnd.randint(-2500, 2500), 12),
                        ("Água", 6500 + self.rnd.randint(-800, 800), 12), ("Material de limpeza", 9000, 20)]
            if mes % 3 == 0:
                despesas.append(("Manutenção dos aparelhos", 45000, 22))
            for desc, valor, dia in despesas:
                d = date(ano, mes, dia)
                if d <= self.hoje:
                    lanca(tipo="saida", data=d.isoformat(), valorCentavos=valor, descricao=desc,
                          formaPagamento="transferencia" if valor > 20000 else "pix")

    def agenda(self, perfis: list[dict], profs: list[dict]):
        repo = rep_ag.AgendaRepository(self.c, self.t)
        ativos = [p for p in perfis if p.get("ativo", True)]
        d = self.hoje - timedelta(days=95)  # dentro da retenção de 4 meses
        while d <= self.hoje + timedelta(days=7):
            if d.weekday() < 6:
                for _ in range(self.rnd.choice((0, 1, 1, 2))):
                    prof = self.rnd.choice(profs) if profs and self.rnd.random() > 0.15 else None
                    hora = self.rnd.choice(HORAS)
                    if self.rnd.random() < 0.3:
                        nome, pid = self.rnd.choice(NOVOS_AGENDA), None
                    else:
                        p = self.rnd.choice(ativos)
                        nome, pid = p["nome"], p["id"]
                    a = repo.create(d.isoformat(), hora, pid, nome, None,
                                    prof["id"] if prof else None, prof["nome"] if prof else None)
                    self.anota(rep_ag._pk(self.c), rep_ag._sk(d.isoformat(), hora, a["id"]))
            d += timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clinic-id", required=True)
    ap.add_argument("--table-name", required=True)
    ap.add_argument("--desfazer", action="store_true", help="Apaga o que este script criou")
    args = ap.parse_args()
    if args.clinic_id in PROTEGIDAS:
        print("ERRO: clínica de cliente real. Este script é só para demonstração.", file=sys.stderr)
        return 1
    manifesto = RAIZ / "scripts" / "demo" / f"{args.clinic_id}.json"
    table = boto3.resource("dynamodb", region_name="us-east-1").Table(args.table_name)

    if args.desfazer:
        if not manifesto.exists():
            print(f"Nada a desfazer: {manifesto} não existe.")
            return 0
        chaves = json.loads(manifesto.read_text(encoding="utf-8"))
        with table.batch_writer() as bw:
            for k in chaves:
                bw.delete_item(Key=k)
        manifesto.rename(manifesto.with_suffix(".desfeito.json"))
        print(f"Apagados {len(chaves)} itens criados pelo script.")
        return 0

    if manifesto.exists():
        print(f"ERRO: já existe {manifesto}. Rode --desfazer antes de semear de novo.", file=sys.stderr)
        return 1

    s = Semeador(args.clinic_id, args.table_name)
    manifesto.parent.mkdir(parents=True, exist_ok=True)
    try:
        profs = [p for p in s._catalogo("PROFISSIONAL#")]
        aparelhos = [{"id": a["id"], "nome": a["nome"]} for a in s._catalogo("APARELHO#")]
        treinos = [t["nome"] for t in s._catalogo("TREINO#")] or ["Força", "Mobilidade"]
        existentes = rep_pac.PacienteRepository(s.c, s.t).list_ativos()
        novos = s.alunos()
        perfis = existentes + novos
        planos = s.planos(perfis)
        s.escala(novos)
        s.aulas(perfis, planos, profs, aparelhos, treinos)
        s.caixa(perfis, planos)
        s.agenda(perfis, profs)
    finally:
        manifesto.write_text(json.dumps(s.criados, ensure_ascii=False), encoding="utf-8")
    print(f"Criados {len(s.criados)} itens na clínica {args.clinic_id}.")
    print(f"Manifesto (para desfazer): {manifesto}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
