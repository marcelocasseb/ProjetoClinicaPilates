"""Conta das mensalidades do mês: previsto × recebido × em aberto, aluno a aluno.

Função pura (sem DynamoDB), usada pela tela Mensalidades (`GET /financeiro/mensalidades`)
e pelo relatório Financeiro (`GET /relatorios/financeiro`). Uma fonte só garante que os
dois mostrem os mesmos números (REL-06).
"""
from app.schemas_financeiro import TIPO_ENTRADA
from app.schemas_plano import (
    STATUS_ABERTO,
    STATUS_ISENTO,
    STATUS_PAGO,
    STATUS_PARCIAL,
    STATUS_SEM_PLANO,
)


def status_mensalidade(tem_plano: bool, valor: int, pago: int) -> str:
    """Situação da mensalidade do aluno no mês.

    "Sem plano" e "isento" são estados **diferentes**: o primeiro é alguém que ninguém
    definiu quanto paga (precisa de ação); o segundo é bolsista/cortesia (está resolvido).
    Tratar os dois como "R$ 0,00" esconderia trabalho pendente.
    """
    if not tem_plano:
        return STATUS_SEM_PLANO
    if valor == 0:
        return STATUS_ISENTO
    if pago >= valor:
        return STATUS_PAGO
    if pago > 0:
        return STATUS_PARCIAL
    return STATUS_ABERTO


def calcular_mensalidades(
    mes: str,
    alunos: list[dict],
    planos: list[dict],
    lancamentos_competencia: list[dict],
    matriculas_escala: list[dict],
) -> dict:
    """Monta o corpo de `MensalidadesOut` a partir dos dados já lidos.

    - `alunos`: perfis ativos (`id`, `nome`).
    - `planos`: um por aluno (`pacienteId`, `valorCentavos`, `frequencia`, `diaVencimento`).
    - `lancamentos_competencia`: lançamentos com `competencia == mes`; só entradas contam.
    - `matriculas_escala`: itens da grade; servem só para apontar divergência com o plano.
    """
    por_paciente = {p["pacienteId"]: p for p in planos}

    pago_por_aluno: dict[str, int] = {}
    for lanc in lancamentos_competencia:
        if lanc.get("tipo") != TIPO_ENTRADA:
            continue
        pid = lanc.get("pacienteId")
        pago_por_aluno[pid] = pago_por_aluno.get(pid, 0) + lanc["valorCentavos"]

    # Quantos horários cada aluno ocupa na grade (0 se a clínica não usa a Escala).
    horarios_por_aluno: dict[str, int] = {}
    for m in matriculas_escala:
        pid = m["pacienteId"]
        horarios_por_aluno[pid] = horarios_por_aluno.get(pid, 0) + 1

    linhas = []
    previsto = recebido = em_aberto = 0
    for p in alunos:
        pid = p["id"]
        plano = por_paciente.get(pid)
        tem_plano = plano is not None
        valor = int(plano.get("valorCentavos") or 0) if tem_plano else 0
        pago = pago_por_aluno.get(pid, 0)
        # Em aberto é somado **por aluno**: se um pagou a mais, isso não pode mascarar
        # a dívida de outro no total da clínica.
        aberto = max(0, valor - pago)
        freq_plano = plano.get("frequencia") if tem_plano else None
        freq_escala = horarios_por_aluno.get(pid)

        previsto += valor
        recebido += pago
        em_aberto += aberto

        linhas.append(
            {
                "pacienteId": pid,
                "nome": p.get("nome") or "",
                "valorCentavos": valor,
                "pagoCentavos": pago,
                "emAbertoCentavos": aberto,
                "diaVencimento": plano.get("diaVencimento") if tem_plano else None,
                "frequencia": freq_plano,
                "frequenciaEscala": freq_escala,
                "divergenciaEscala": bool(
                    freq_plano and freq_escala and freq_plano != freq_escala
                ),
                "temPlano": tem_plano,
                "status": status_mensalidade(tem_plano, valor, pago),
            }
        )

    linhas.sort(key=lambda l: l["nome"].lower())
    return {
        "mes": mes,
        "previstoCentavos": previsto,
        "recebidoCentavos": recebido,
        "emAbertoCentavos": em_aberto,
        "alunos": linhas,
    }
