// Tela de Mensalidades — previsto × recebido × em aberto do mês (fluxo-caixa F2).
//
// A lista sai do CADASTRO de pacientes, não da Escala: numa clínica que não usa a
// grade, esta tela funciona igual. A Escala entra só para apontar divergência
// ("o plano diz 2x por semana, mas o aluno está em 3 horários na grade").
//
// Registrar o pagamento aqui cria um lançamento de entrada no caixa com `competencia`
// = o mês exibido — é o que faz "mensalidade de setembro paga em outubro" aparecer
// como paga em setembro sem mentir sobre quando o dinheiro entrou.
import { Fragment, useEffect, useState } from "react";
import { financeiroApi } from "../api";
import {
  FORMAS_PAGAMENTO,
  brParaCentavos,
  centavosParaBR,
  formatMesBR,
  hojeISO,
  maskMoeda,
} from "../utils/format";

// Sem acento e em minúsculas — buscar "jose" tem que achar "José".
// `NFD` separa a letra do acento; o range abaixo é o bloco de diacríticos
// combinantes do Unicode. O range é escrito com sequência de escape de propósito: os
// caracteres literais são invisíveis no editor e somem numa conversão de encoding.
const semAcento = (t) =>
  (t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const VAZIO = { previstoCentavos: 0, recebidoCentavos: 0, emAbertoCentavos: 0, alunos: [] };

const STATUS = {
  pago: { label: "pago", classe: "st-pago" },
  parcial: { label: "parcial", classe: "st-parcial" },
  aberto: { label: "em aberto", classe: "st-aberto" },
  isento: { label: "isento", classe: "st-isento" },
  sem_plano: { label: "definir valor", classe: "st-sem-plano" },
};

export default function Mensalidades({ clinic, mes, aoMexerNoCaixa }) {
  const [dados, setDados] = useState(VAZIO);
  const [precos, setPrecos] = useState({ tabelaPrecos: [] });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [editando, setEditando] = useState(null); // pacienteId com o form de plano aberto
  const [form, setForm] = useState({ valor: "", diaVencimento: "", frequencia: "" });
  const [cobrando, setCobrando] = useState(null); // pacienteId com o form de baixa aberto
  const [valorPago, setValorPago] = useState("");
  const [formaPago, setFormaPago] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [filtroVenc, setFiltroVenc] = useState("");

  async function carregar() {
    setErro("");
    setCarregando(true);
    try {
      const [m, cfg] = await Promise.all([
        financeiroApi.mensalidades(clinic.id, mes),
        financeiroApi.config(clinic.id),
      ]);
      setDados(m);
      setPrecos(cfg);
    } catch (e) {
      setErro(e.message);
      setDados(VAZIO);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, [clinic.id, mes]);

  function abrirPlano(aluno) {
    setCobrando(null);
    setEditando(aluno.pacienteId);
    setForm({
      valor: aluno.temPlano ? centavosParaBR(aluno.valorCentavos) : "",
      diaVencimento: aluno.diaVencimento ? String(aluno.diaVencimento) : "",
      // Sem plano ainda: a grade sugere a frequência — é o único papel dela aqui.
      frequencia: String(aluno.frequencia || aluno.frequenciaEscala || ""),
    });
  }

  // Escolher a frequência preenche o valor pela tabela de preços (se houver).
  function escolherFrequencia(freq) {
    const faixa = (precos.tabelaPrecos || []).find((f) => String(f.frequencia) === String(freq));
    setForm((f) => ({
      ...f,
      frequencia: freq,
      valor: faixa ? centavosParaBR(faixa.valorCentavos) : f.valor,
    }));
  }

  async function salvarPlano(pacienteId) {
    setErro("");
    setSalvando(true);
    try {
      await financeiroApi.definirPlano(clinic.id, pacienteId, {
        valorCentavos: brParaCentavos(form.valor),
        diaVencimento: form.diaVencimento ? Number(form.diaVencimento) : null,
        frequencia: form.frequencia ? Number(form.frequencia) : null,
      });
      setEditando(null);
      await carregar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  async function removerPlano(pacienteId) {
    if (!window.confirm("Tirar o plano deste aluno? Ele volta para “definir valor”.")) return;
    setErro("");
    try {
      await financeiroApi.removerPlano(clinic.id, pacienteId);
      setEditando(null);
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  function abrirBaixa(aluno) {
    setEditando(null);
    setCobrando(aluno.pacienteId);
    setValorPago(centavosParaBR(aluno.emAbertoCentavos || aluno.valorCentavos));
    setFormaPago("");
  }

  async function registrarPagamento(aluno) {
    const centavos = brParaCentavos(valorPago);
    if (centavos <= 0) return setErro("Informe um valor maior que zero.");

    setErro("");
    setSalvando(true);
    try {
      // A data é HOJE (quando o dinheiro entrou — regime de caixa); a competência é o
      // mês EXIBIDO. Os dois separados é o que faz o atrasado cair no lugar certo.
      await financeiroApi.criar(clinic.id, {
        tipo: "entrada",
        data: hojeISO(),
        valorCentavos: centavos,
        descricao: `Mensalidade ${formatMesBR(mes)} — ${aluno.nome}`,
        pacienteId: aluno.pacienteId,
        competencia: mes,
        formaPagamento: formaPago || null,
      });
      setCobrando(null);
      // O Caixa continua montado atrás desta tela: sem este aviso, o extrato só
      // mostraria o recebimento depois de um F5.
      aoMexerNoCaixa?.();
      await carregar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  // Os dias de vencimento oferecidos no filtro são os que EXISTEM nesta clínica —
  // um combo de 1 a 31 com 28 opções mortas só atrapalharia.
  const vencimentosEmUso = [
    ...new Set(dados.alunos.map((a) => a.diaVencimento).filter(Boolean)),
  ].sort((a, b) => a - b);

  const alunosFiltrados = dados.alunos.filter((a) => {
    if (busca && !semAcento(a.nome).includes(semAcento(busca))) return false;
    if (filtroStatus && a.status !== filtroStatus) return false;
    if (filtroVenc && String(a.diaVencimento || "") !== filtroVenc) return false;
    return true;
  });

  const filtrando = Boolean(busca || filtroStatus || filtroVenc);

  const pct = dados.previstoCentavos
    ? Math.round((dados.recebidoCentavos / dados.previstoCentavos) * 100)
    : 0;
  const inadimplentes = dados.alunos.filter((a) => a.emAbertoCentavos > 0).length;
  const semPlano = dados.alunos.filter((a) => !a.temPlano).length;

  return (
    <div>
      {erro && <div className="erro">{erro}</div>}

      <div className="card">
        <div className="fin-totais">
          <div className="fin-total saldo">
            <span className="fin-rotulo">Previsto</span>
            <strong>R$ {centavosParaBR(dados.previstoCentavos)}</strong>
          </div>
          <div className="fin-total entrada">
            <span className="fin-rotulo">Recebido</span>
            <strong>R$ {centavosParaBR(dados.recebidoCentavos)}</strong>
            <span className="muted">{pct}% do previsto</span>
          </div>
          <div
            className={dados.emAbertoCentavos > 0 ? "fin-total saida" : "fin-total entrada"}
          >
            <span className="fin-rotulo">Em aberto</span>
            <strong>R$ {centavosParaBR(dados.emAbertoCentavos)}</strong>
            <span className="muted">
              {inadimplentes === 0 ? "ninguém devendo" : `${inadimplentes} aluno(s)`}
            </span>
          </div>
        </div>
        {semPlano > 0 && (
          <p className="muted" style={{ marginTop: 12 }}>
            ⚠️ {semPlano} aluno(s) ainda sem valor definido — eles não entram no previsto.
          </p>
        )}
      </div>

      <div className="card">
        <h3>
          Alunos — {formatMesBR(mes)}{" "}
          <span className="muted" style={{ fontWeight: 400, fontSize: 14 }}>
            ({filtrando
              ? `${alunosFiltrados.length} de ${dados.alunos.length}`
              : dados.alunos.length}
            )
          </span>
        </h3>

        <div className="fin-filtros">
          <input
            className="search"
            placeholder="Buscar aluno…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
          <select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
            <option value="">Todas as situações</option>
            <option value="aberto">Em aberto</option>
            <option value="parcial">Parcial</option>
            <option value="pago">Pago</option>
            <option value="isento">Isento</option>
            <option value="sem_plano">Sem valor definido</option>
          </select>
          <select value={filtroVenc} onChange={(e) => setFiltroVenc(e.target.value)}>
            <option value="">Todos os vencimentos</option>
            {vencimentosEmUso.map((d) => (
              <option key={d} value={String(d)}>
                Vence dia {d}
              </option>
            ))}
          </select>
          {filtrando && (
            <button
              type="button"
              className="link"
              onClick={() => {
                setBusca("");
                setFiltroStatus("");
                setFiltroVenc("");
              }}
            >
              limpar filtros
            </button>
          )}
        </div>
        {carregando ? (
          <div className="loading">
            <span className="spinner" />
            Carregando as mensalidades…
          </div>
        ) : dados.alunos.length === 0 ? (
          <p className="muted">
            Nenhum aluno ativo no cadastro. Cadastre pacientes na aba Pacientes para começar a
            cobrar.
          </p>
        ) : alunosFiltrados.length === 0 ? (
          <p className="muted">Nenhum aluno com esses filtros.</p>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Freq.</th>
                  <th className="num">Valor</th>
                  <th>Venc.</th>
                  <th className="num">Pago</th>
                  <th>Situação</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {alunosFiltrados.map((a) => {
                  const st = STATUS[a.status] || STATUS.sem_plano;
                  return (
                    <Fragment key={a.pacienteId}>
                      <tr>
                        <td>
                          {a.nome}
                          {a.divergenciaEscala && (
                            <span
                              className="chip-alerta"
                              title={`O plano diz ${a.frequencia}x por semana, mas o aluno está em ${a.frequenciaEscala} horários na Escala`}
                            >
                              ⚠ grade: {a.frequenciaEscala}x
                            </span>
                          )}
                        </td>
                        <td>{a.frequencia ? `${a.frequencia}x/sem` : "—"}</td>
                        <td className="num">
                          {a.temPlano ? `R$ ${centavosParaBR(a.valorCentavos)}` : "—"}
                        </td>
                        <td>{a.diaVencimento ? `dia ${a.diaVencimento}` : "—"}</td>
                        <td className="num">
                          {a.pagoCentavos > 0 ? `R$ ${centavosParaBR(a.pagoCentavos)}` : "—"}
                        </td>
                        <td>
                          <span className={`st ${st.classe}`}>{st.label}</span>
                        </td>
                        <td className="td-actions">
                          {a.temPlano && a.emAbertoCentavos > 0 && (
                            <button
                              type="button"
                              className="link"
                              onClick={() => abrirBaixa(a)}
                            >
                              dar baixa
                            </button>
                          )}{" "}
                          <button type="button" className="link" onClick={() => abrirPlano(a)}>
                            {a.temPlano ? "editar" : "definir valor"}
                          </button>
                        </td>
                      </tr>

                      {editando === a.pacienteId && (
                        <tr className="linha-form">
                          <td colSpan={7}>
                            <div className="fin-form">
                              <label className="fin-campo">
                                <span>Frequência</span>
                                <select
                                  value={form.frequencia}
                                  onChange={(e) => escolherFrequencia(e.target.value)}
                                >
                                  <option value="">—</option>
                                  {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                                    <option key={n} value={n}>
                                      {n}x por semana
                                    </option>
                                  ))}
                                </select>
                              </label>
                              <label className="fin-campo">
                                <span>Valor mensal</span>
                                <input
                                  inputMode="numeric"
                                  placeholder="0,00"
                                  value={form.valor}
                                  onChange={(e) =>
                                    setForm((f) => ({ ...f, valor: maskMoeda(e.target.value) }))
                                  }
                                />
                              </label>
                              <label className="fin-campo">
                                <span>Vencimento</span>
                                <select
                                  value={form.diaVencimento}
                                  onChange={(e) =>
                                    setForm((f) => ({ ...f, diaVencimento: e.target.value }))
                                  }
                                >
                                  <option value="">—</option>
                                  {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                                    <option key={d} value={d}>
                                      dia {d}
                                    </option>
                                  ))}
                                </select>
                              </label>
                              <button
                                type="button"
                                className="btn primary"
                                disabled={salvando}
                                onClick={() => salvarPlano(a.pacienteId)}
                              >
                                Salvar
                              </button>
                              <button
                                type="button"
                                className="btn"
                                onClick={() => setEditando(null)}
                              >
                                Cancelar
                              </button>
                              {a.temPlano && (
                                <button
                                  type="button"
                                  className="link danger"
                                  onClick={() => removerPlano(a.pacienteId)}
                                >
                                  tirar plano
                                </button>
                              )}
                            </div>
                            <p className="muted" style={{ marginTop: 6 }}>
                              Valor 0,00 = bolsista/cortesia (aparece como “isento”, não como
                              dívida).
                            </p>
                          </td>
                        </tr>
                      )}

                      {cobrando === a.pacienteId && (
                        <tr className="linha-form">
                          <td colSpan={7}>
                            <div className="fin-form">
                              <label className="fin-campo">
                                <span>Valor recebido</span>
                                <input
                                  inputMode="numeric"
                                  value={valorPago}
                                  onChange={(e) => setValorPago(maskMoeda(e.target.value))}
                                />
                              </label>
                              <label className="fin-campo">
                                <span>Forma</span>
                                <select
                                  value={formaPago}
                                  onChange={(e) => setFormaPago(e.target.value)}
                                >
                                  {FORMAS_PAGAMENTO.map((f) => (
                                    <option key={f.v} value={f.v}>
                                      {f.label}
                                    </option>
                                  ))}
                                </select>
                              </label>
                              <button
                                type="button"
                                className="btn primary"
                                disabled={salvando}
                                onClick={() => registrarPagamento(a)}
                              >
                                Registrar pagamento
                              </button>
                              <button
                                type="button"
                                className="btn"
                                onClick={() => setCobrando(null)}
                              >
                                Cancelar
                              </button>
                            </div>
                            <p className="muted" style={{ marginTop: 6 }}>
                              Entra no caixa com a data de <strong>hoje</strong> e competência{" "}
                              <strong>{formatMesBR(mes)}</strong>.
                            </p>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
