"""Agregações dos relatórios (aba Relatórios, só admin). Funções puras, sem I/O.

Os routers leem os dados nos repositórios e chamam estas funções; a tela, o PDF de um
relatório e o fechamento do mês usam a mesma resposta, então mostram os mesmos números.

Convenções:
- Valores em **centavos inteiros**; mês como `AAAA-MM`; datas como `AAAA-MM-DD`.
- Timestamps (`criadoEm`/`atualizadoEm`, ISO em UTC) são lidos no **horário de Brasília**
  (UTC−3 fixo; o Brasil não tem horário de verão desde 2019). Assim um aluno cadastrado às
  22h do dia 31 conta no mês certo.
- Na Agenda, mês ou semana além da retenção (4 meses, TTL) vale `None` ("sem dados"),
  nunca zero: um zero diria que ninguém foi marcado, o que seria falso.
"""
from datetime import date, datetime, timedelta, timezone

from app.repository_agenda import expira_em
from app.schemas_financeiro import TIPO_ENTRADA
from app.schemas_plano import (
    STATUS_ABERTO,
    STATUS_ISENTO,
    STATUS_PAGO,
    STATUS_PARCIAL,
    STATUS_SEM_PLANO,
)

FUSO_BRASILIA = timezone(timedelta(hours=-3))
SEM_PROFISSIONAL = "Sem profissional"
FORMA_NAO_INFORMADA = "nao_informado"
_DIAS_ABREV = {1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb", 7: "Dom"}

# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------


def mes_local(ts: str) -> str:
    """Mês (`AAAA-MM`) de um timestamp ISO, no horário de Brasília."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_BRASILIA).strftime("%Y-%m")


def data_local(ts: str) -> str:
    """Data (`AAAA-MM-DD`) de um timestamp ISO, no horário de Brasília."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_BRASILIA).date().isoformat()


def hoje_local() -> date:
    return datetime.now(FUSO_BRASILIA).date()


def meses_entre(de: str, ate: str) -> list[str]:
    """Meses (`AAAA-MM`) tocados pelo período `de`..`ate`, em ordem."""
    a = int(de[:4]) * 12 + int(de[5:7]) - 1
    b = int(ate[:4]) * 12 + int(ate[5:7]) - 1
    return [f"{(t // 12):04d}-{(t % 12) + 1:02d}" for t in range(a, b + 1)]


def meses_evolucao(de: str, ate: str) -> list[str]:
    """Meses do gráfico de evolução: os do período; se ele cabe num mês só, os 12 meses
    que terminam nele (para dar contexto)."""
    meses = meses_entre(de, ate)
    return meses if len(meses) >= 2 else meses_ate(ate[:7])


def no_periodo(itens: list[dict], de: str, ate: str) -> list[dict]:
    """Itens com `data` (`AAAA-MM-DD`) dentro de `de`..`ate`, inclusive."""
    return [i for i in itens if de <= (i.get("data") or "") <= ate]


def meses_ate(mes: str, n: int = 12) -> list[str]:
    """Os `n` meses que terminam em `mes`, em ordem cronológica."""
    ano, m = int(mes[:4]), int(mes[5:7])
    total = ano * 12 + (m - 1)
    return [f"{(t // 12):04d}-{(t % 12) + 1:02d}" for t in range(total - n + 1, total + 1)]


def ultimo_dia(mes: str) -> str:
    ano, m = int(mes[:4]), int(mes[5:7])
    proximo = date(ano + (m == 12), m % 12 + 1, 1)
    return (proximo - timedelta(days=1)).isoformat()


def segunda_da_semana(data: str) -> str:
    d = date.fromisoformat(data)
    return (d - timedelta(days=d.weekday())).isoformat()


def meses_agenda_disponiveis(meses: list[str], agora: int) -> set[str]:
    """Meses cuja Agenda ainda está inteira: o 1º dia do mês ainda não expirou (TTL).

    `agora` em epoch (s). Se o 1º dia já expirou, parte do mês pode ter sido apagada, e
    mostrar um número parcial seria pior que "sem dados".
    """
    return {m for m in meses if expira_em(f"{m}-01") > agora}


def agenda_disponivel_desde(data: str, agora: int) -> bool:
    return expira_em(data) > agora


# ---------------------------------------------------------------------------
# Financeiro (T4)
# ---------------------------------------------------------------------------


def resumo_caixa(lancamentos: list[dict]) -> dict:
    """Mesma conta do `GET /financeiro/lancamentos`."""
    entradas = sum(l["valorCentavos"] for l in lancamentos if l["tipo"] == TIPO_ENTRADA)
    saidas = sum(l["valorCentavos"] for l in lancamentos if l["tipo"] != TIPO_ENTRADA)
    return {"entradasCentavos": entradas, "saidasCentavos": saidas, "saldoCentavos": entradas - saidas}


def receita_por_forma(lancamentos: list[dict]) -> list[dict]:
    """Entradas agrupadas por forma de pagamento, maior valor primeiro.

    `cartao` (forma antiga, antes de crédito/débito) fica como está e o front rotula
    "Cartão (antigo)"; entrada sem forma vira `nao_informado`.
    """
    por_forma: dict[str, int] = {}
    for l in lancamentos:
        if l["tipo"] != TIPO_ENTRADA:
            continue
        forma = (l.get("formaPagamento") or "").strip().lower() or FORMA_NAO_INFORMADA
        por_forma[forma] = por_forma.get(forma, 0) + l["valorCentavos"]
    total = sum(por_forma.values())
    linhas = [
        {"forma": f, "valorCentavos": v, "pct": round(v * 100 / total, 1) if total else 0.0}
        for f, v in por_forma.items()
    ]
    linhas.sort(key=lambda x: (-x["valorCentavos"], x["forma"]))
    return linhas


def resumo_mensalidades(mensalidades: dict) -> dict:
    """Totais + quantos alunos em cada situação, a partir de `calcular_mensalidades`."""
    por_status = {s: 0 for s in (STATUS_PAGO, STATUS_PARCIAL, STATUS_ABERTO, STATUS_ISENTO, STATUS_SEM_PLANO)}
    for a in mensalidades["alunos"]:
        por_status[a["status"]] = por_status.get(a["status"], 0) + 1
    return {
        "previstoCentavos": mensalidades["previstoCentavos"],
        "recebidoCentavos": mensalidades["recebidoCentavos"],
        "emAbertoCentavos": mensalidades["emAbertoCentavos"],
        "porStatus": por_status,
    }


def extrato(lancamentos: list[dict]) -> list[dict]:
    """Lançamentos do mês para impressão, na ordem do Caixa (`list_mes` já ordena)."""
    campos = ("data", "descricao", "formaPagamento", "tipo", "valorCentavos")
    return [{c: l.get(c) for c in campos} for l in lancamentos]


# ---------------------------------------------------------------------------
# Alunos (T5)
# ---------------------------------------------------------------------------


def _mes_saida(perfil: dict):
    """Mês em que o aluno foi removido, ou `None` se está ativo.

    Perfil removido não é mais editado, então o `atualizadoEm` dele é a data da remoção.
    """
    if perfil.get("ativo", True):
        return None
    return mes_local(perfil.get("atualizadoEm") or perfil["criadoEm"])


def _ativo_no_fim(perfil: dict, mes: str) -> bool:
    if mes_local(perfil["criadoEm"]) > mes:
        return False
    saida = _mes_saida(perfil)
    return saida is None or saida > mes


def _contagens_mes(perfis: list[dict], mes: str) -> dict:
    return {
        "ativos": sum(1 for p in perfis if _ativo_no_fim(p, mes)),
        "novos": sum(1 for p in perfis if mes_local(p["criadoEm"]) == mes),
        "saidas": sum(1 for p in perfis if _mes_saida(p) == mes),
    }


def indicadores_periodo(perfis: list[dict], de: str, ate: str) -> dict:
    """Novos e saídas dentro de `de`..`ate` e ativos no fim do período (datas em Brasília)."""

    def saida(p):
        if p.get("ativo", True):
            return None
        return data_local(p.get("atualizadoEm") or p["criadoEm"])

    novos = sorted(
        (p for p in perfis if de <= data_local(p["criadoEm"]) <= ate), key=lambda p: p["criadoEm"]
    )
    ativos_fim = sum(
        1 for p in perfis if data_local(p["criadoEm"]) <= ate and (saida(p) is None or saida(p) > ate)
    )
    return {
        "ativosFimMes": ativos_fim,
        "novos": len(novos),
        "saidas": sum(1 for p in perfis if (s := saida(p)) and de <= s <= ate),
        "novosLista": [{"id": p["id"], "nome": p.get("nome") or "", "criadoEm": p["criadoEm"]} for p in novos],
    }


def indicadores_alunos(perfis: list[dict], mes: str) -> dict:
    return indicadores_periodo(perfis, f"{mes}-01", ultimo_dia(mes))


def evolucao_alunos(perfis: list[dict], meses: list[str]) -> list[dict]:
    return [{"mes": m, **_contagens_mes(perfis, m)} for m in meses]


def carteira_planos(planos: list[dict], alunos_ativos: list[dict]) -> dict:
    """Planos dos alunos **ativos**: total mensal, ticket médio (sem isentos), frequências."""
    ativos = {a["id"] for a in alunos_ativos}
    dos_ativos = [p for p in planos if p["pacienteId"] in ativos]
    pagantes = [p for p in dos_ativos if int(p.get("valorCentavos") or 0) > 0]
    total = sum(int(p["valorCentavos"]) for p in pagantes)

    por_freq: dict = {}
    for p in dos_ativos:
        f = p.get("frequencia")
        f = int(f) if f is not None else None
        por_freq[f] = por_freq.get(f, 0) + 1
    frequencias = sorted(por_freq.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))

    return {
        "totalMensalCentavos": total,
        "ticketMedioCentavos": round(total / len(pagantes)) if pagantes else 0,
        "comPlano": len(pagantes),
        "isentos": len(dos_ativos) - len(pagantes),
        "semPlano": len(ativos - {p["pacienteId"] for p in dos_ativos}),
        "porFrequencia": [{"frequencia": f, "alunos": n} for f, n in frequencias],
    }


def relacao_alunos(alunos_ativos: list[dict], planos: list[dict], matriculas: list[dict]) -> list[dict]:
    """Relação dos alunos ativos (contato, plano, horários), em ordem alfabética."""
    plano_de = {p["pacienteId"]: p for p in planos}
    horarios: dict[str, list] = {}
    for m in matriculas:
        horarios.setdefault(m["pacienteId"], []).append((int(m["dia"]), m["hora"]))

    linhas = []
    for a in alunos_ativos:
        plano = plano_de.get(a["id"])
        valor = int(plano.get("valorCentavos") or 0) if plano else 0
        linhas.append(
            {
                "id": a["id"],
                "nome": a.get("nome") or "",
                "telefone": a.get("telefone"),
                "email": a.get("email"),
                "dataNascimento": a.get("dataNascimento"),
                "plano": {
                    "valorCentavos": valor,
                    "frequencia": plano.get("frequencia"),
                    "diaVencimento": plano.get("diaVencimento"),
                }
                if plano
                else None,
                "isento": bool(plano) and valor == 0,
                "horarios": [f"{_DIAS_ABREV[d]} {h}" for d, h in sorted(horarios.get(a["id"], []))],
            }
        )
    linhas.sort(key=lambda l: l["nome"].lower())
    return linhas


# ---------------------------------------------------------------------------
# Ocupação (T6)
# ---------------------------------------------------------------------------


def ocupacao(matriculas: list[dict], alunos_ativos: list[dict]) -> dict:
    """Ocupação da grade **atual** (a escala não guarda histórico).

    Matrícula de aluno removido é ignorada, como o `GET /escala` já faz.
    """
    ativos = {a["id"]: a for a in alunos_ativos}
    validas = [m for m in matriculas if m["pacienteId"] in ativos]

    por_celula: dict[tuple, int] = {}
    for m in validas:
        chave = (int(m["dia"]), m["hora"])
        por_celula[chave] = por_celula.get(chave, 0) + 1
    celulas = [{"dia": d, "hora": h, "alunos": n} for (d, h), n in sorted(por_celula.items())]

    na_grade = {m["pacienteId"] for m in validas}
    fora = sorted(
        ({"id": a["id"], "nome": a.get("nome") or ""} for pid, a in ativos.items() if pid not in na_grade),
        key=lambda a: a["nome"].lower(),
    )
    return {
        "celulas": celulas,
        "matriculas": len(validas),
        "alunosDistintos": len(na_grade),
        "mediaPorHorarioOcupado": round(len(validas) / len(celulas), 1) if celulas else 0,
        "top5": sorted(celulas, key=lambda c: (-c["alunos"], c["dia"], c["hora"]))[:5],
        "foraDaEscala": fora,
    }


# ---------------------------------------------------------------------------
# Atendimento (T7) e semana (T8)
# ---------------------------------------------------------------------------


def _chave_profissional(item: dict, nome_snapshot: str, profissionais: dict):
    """(chave, id, nome) do profissional de uma aula ou marcação.

    Com id, agrupa pelo cadastro (o nome vem ao vivo do cadastro; sem ele, do snapshot).
    Sem id, agrupa pelo texto livre das aulas antigas. Sem nada, "Sem profissional".
    """
    pid = item.get("profissionalId")
    if pid:
        return ("id", pid), pid, profissionais.get(pid) or nome_snapshot or SEM_PROFISSIONAL
    texto = (nome_snapshot or "").strip()
    if texto:
        return ("txt", texto.lower()), None, texto
    return ("nenhum",), None, SEM_PROFISSIONAL


def _chave_aluno(item: dict, nomes: dict):
    """(chave, pacienteId, nome, novo): aluno cadastrado pelo id; aluno novo da Agenda
    (sem cadastro) pelo nome digitado, sem diferenciar maiúsculas."""
    pid = item.get("pacienteId")
    if pid:
        return ("id", pid), pid, nomes.get(pid) or item.get("nome") or "", False
    nome = (item.get("nome") or "").strip()
    return ("novo", nome.lower()), None, nome, True


def _ordenar(linhas: list[dict]) -> list[dict]:
    return sorted(linhas, key=lambda l: (-(l["aulas"] + (l["agenda"] or 0)), l["nome"].lower()))


def _ranking(contagem: dict) -> list[dict]:
    return [{"nome": n, "aulas": c} for n, c in sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0].lower()))]


def atendimento(
    sessoes: list[dict],
    agenda: list[dict],
    perfis: list[dict],
    profissionais: dict,
    periodo: tuple[str, str],
    meses: list[str],
    disponiveis: set,
    agenda_ok: bool,
) -> dict:
    """Aulas registradas (Pilates) e marcações da Agenda, **separadas, nunca somadas**.

    `periodo`: (de, ate) em `AAAA-MM-DD`. `profissionais`: {id: nome} do cadastro
    (inclui removidos). `meses`/`disponiveis`: eixo da evolução e meses em que a Agenda
    ainda está inteira. `agenda_ok`: a Agenda cobre o período inteiro (senão "s/d").
    """
    de, ate = periodo
    nomes = {p["id"]: p.get("nome") or "" for p in perfis}
    sessoes_mes = no_periodo(sessoes, de, ate)
    agenda_mes = no_periodo(agenda, de, ate) if agenda_ok else []

    profs: dict = {}
    alunos: dict = {}

    def _somar(item, nome_prof, fonte):
        chave, pid, nome = _chave_profissional(item, nome_prof, profissionais)
        linha = profs.setdefault(
            chave, {"profissionalId": pid, "nome": nome, "aulas": 0, "agenda": 0 if agenda_ok else None}
        )
        linha[fonte] += 1
        chave, pac, nome, novo = _chave_aluno(item, nomes)
        linha = alunos.setdefault(
            chave, {"pacienteId": pac, "nome": nome, "novo": novo, "aulas": 0, "agenda": 0 if agenda_ok else None}
        )
        linha[fonte] += 1

    aparelhos: dict[str, int] = {}
    treinos: dict[str, int] = {}
    for s in sessoes_mes:
        _somar(s, s.get("profissional"), "aulas")
        # Cada aparelho e cada treino conta 1 por aula em que aparece.
        for nome in {a.get("nome") for a in s.get("aparelhos") or [] if a.get("nome")}:
            aparelhos[nome] = aparelhos.get(nome, 0) + 1
        nomes_treinos = {t for a in s.get("aparelhos") or [] for t in a.get("treinos") or [] if t}
        for t in nomes_treinos:
            treinos[t] = treinos.get(t, 0) + 1
    for a in agenda_mes:
        _somar(a, a.get("profissionalNome"), "agenda")

    def _conta(itens, m):
        return sum(1 for i in itens if (i.get("data") or "")[:7] == m)

    return {
        "de": de,
        "ate": ate,
        "totalAulas": len(sessoes_mes),
        "totalAgenda": len(agenda_mes) if agenda_ok else None,
        "evolucao": [
            {"mes": m, "aulas": _conta(sessoes, m), "agenda": _conta(agenda, m) if m in disponiveis else None}
            for m in meses
        ],
        "porProfissional": _ordenar(list(profs.values())),
        "porAluno": _ordenar(list(alunos.values())),
        "aparelhos": _ranking(aparelhos),
        "treinos": _ranking(treinos),
    }


def semana(
    sessoes: list[dict],
    agenda: list[dict],
    perfis: list[dict],
    inicio: str,
    agenda_disponivel: bool,
) -> dict:
    """Quem passou na semana (segunda `inicio` a domingo): dias × fonte por aluno."""
    d0 = date.fromisoformat(inicio)
    fim = (d0 + timedelta(days=6)).isoformat()
    nomes = {p["id"]: p.get("nome") or "" for p in perfis}
    linhas: dict = {}

    def _somar(item, fonte):
        dia = (date.fromisoformat(item["data"]) - d0).days + 1
        if not 1 <= dia <= 7:
            return
        chave, pac, nome, novo = _chave_aluno(item, nomes)
        linha = linhas.setdefault(
            chave,
            {
                "pacienteId": pac,
                "nome": nome,
                "novo": novo,
                "dias": {str(d): {"aula": 0, "agenda": 0} for d in range(1, 8)},
                "total": 0,
            },
        )
        linha["dias"][str(dia)][fonte] += 1
        linha["total"] += 1

    for s in sessoes:
        _somar(s, "aula")
    if agenda_disponivel:
        for a in agenda:
            _somar(a, "agenda")

    alunos = sorted(linhas.values(), key=lambda l: l["nome"].lower())
    return {
        "inicio": inicio,
        "fim": fim,
        "agendaDisponivel": agenda_disponivel,
        "distintos": len(alunos),
        "totalAulas": sum(d["aula"] for l in alunos for d in l["dias"].values()),
        "totalAgenda": sum(d["agenda"] for l in alunos for d in l["dias"].values()),
        "alunos": alunos,
    }
