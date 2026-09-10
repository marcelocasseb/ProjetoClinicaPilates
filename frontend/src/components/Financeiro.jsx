// Aba Financeiro — livro-caixa mensal da clínica (feature fluxo-caixa, F1).
//
// O mês é a unidade da tela (e da partição no DynamoDB): "‹ Outubro/2026 ›" troca o
// mês inteiro numa Query só. Os três totais NÃO são somados aqui — vêm calculados do
// backend, para que tela e API nunca discordem sobre o saldo.
//
// Dinheiro é inteiro em centavos de ponta a ponta; `maskMoeda`/`brParaCentavos` cuidam
// da digitação e `centavosParaBR` da exibição. Nenhum float encosta no valor.
import { useEffect, useState } from "react";
import { financeiroApi } from "../api";
import Mensalidades from "./Mensalidades";
import TabelaPrecos from "./TabelaPrecos";
import {
  FORMAS_PAGAMENTO,
  brParaCentavos,
  centavosParaBR,
  formatDataBR,
  formatMesBR,
  hojeISO,
  labelForma,
  maskMoeda,
  mesAnterior,
  mesAtual,
  mesSeguinte,
} from "../utils/format";

const CAIXA_VAZIO = {
  entradasCentavos: 0,
  saidasCentavos: 0,
  saldoCentavos: 0,
  lancamentos: [],
};

function formBranco(mes) {
  // Data default = hoje, mas só se hoje pertence ao mês exibido; navegando para um
  // mês passado, o campo abre no dia 1 dele (senão o lançamento cairia noutro mês).
  const hoje = hojeISO();
  return {
    tipo: "saida",
    data: hoje.startsWith(mes) ? hoje : `${mes}-01`,
    valor: "",
    descricao: "",
    formaPagamento: "",
  };
}

export default function Financeiro({ clinic }) {
  // O mês é estado do SHELL, não de cada sub-tela: trocar de "Caixa" para
  // "Mensalidades" mantém o mês que a pessoa estava olhando.
  const [secao, setSecao] = useState("caixa");
  const [mes, setMes] = useState(mesAtual());
  const [caixa, setCaixa] = useState(CAIXA_VAZIO);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState(() => formBranco(mesAtual()));
  // O Caixa fica MONTADO enquanto a pessoa navega pelas sub-abas (só o conteúdo é
  // trocado), então ele não recarrega sozinho quando a aba Mensalidades cria um
  // lançamento. Este contador é o aviso: mudou o dinheiro lá, recarrega aqui.
  const [recarga, setRecarga] = useState(0);

  async function carregar(alvo) {
    setErro("");
    setCarregando(true);
    try {
      setCaixa(await financeiroApi.caixa(clinic.id, alvo));
    } catch (e) {
      setErro(e.message);
      setCaixa(CAIXA_VAZIO);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar(mes);
  }, [clinic.id, mes, recarga]);

  function irPara(novoMes) {
    setMes(novoMes);
    setForm(formBranco(novoMes));
  }

  function setCampo(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  async function salvar() {
    const centavos = brParaCentavos(form.valor);
    if (centavos <= 0) return setErro("Informe um valor maior que zero.");
    if (!form.descricao.trim()) return setErro("Descreva o lançamento.");

    setErro("");
    setSalvando(true);
    try {
      await financeiroApi.criar(clinic.id, {
        tipo: form.tipo,
        data: form.data,
        valorCentavos: centavos,
        descricao: form.descricao.trim(),
        formaPagamento: form.formaPagamento || null,
      });
      // O lançamento pode ter caído em OUTRO mês (data de setembro lançada em
      // outubro): recarregamos o mês da data, e é para lá que a tela navega.
      const mesDoLancamento = form.data.slice(0, 7);
      setForm(formBranco(mesDoLancamento));
      if (mesDoLancamento !== mes) setMes(mesDoLancamento);
      else await carregar(mes);
    } catch (e) {
      // Erro NÃO limpa o formulário — o que foi digitado continua na tela.
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  async function cancelar(lanc) {
    if (!window.confirm(`Cancelar "${lanc.descricao}" de R$ ${centavosParaBR(lanc.valorCentavos)}?`))
      return;
    setErro("");
    try {
      await financeiroApi.cancelar(clinic.id, lanc.data.slice(0, 7), lanc.id);
      await carregar(mes);
    } catch (e) {
      setErro(e.message);
    }
  }

  const vazio = !carregando && caixa.lancamentos.length === 0;

  return (
    <div>
      <nav className="subtabs">
        <button
          type="button"
          className={secao === "caixa" ? "subtab on" : "subtab"}
          onClick={() => setSecao("caixa")}
        >
          Caixa
        </button>
        <button
          type="button"
          className={secao === "mensalidades" ? "subtab on" : "subtab"}
          onClick={() => setSecao("mensalidades")}
        >
          Mensalidades
        </button>
        <button
          type="button"
          className={secao === "precos" ? "subtab on" : "subtab"}
          onClick={() => setSecao("precos")}
        >
          Preços
        </button>
      </nav>

      {secao === "precos" ? (
        <TabelaPrecos clinic={clinic} />
      ) : (
        <>
      {erro && secao === "caixa" && <div className="erro">{erro}</div>}

      <div className="card">
        <div className="fin-mes">
          <button type="button" className="btn" onClick={() => irPara(mesAnterior(mes))}>
            ‹
          </button>
          <h2>{formatMesBR(mes)}</h2>
          <button type="button" className="btn" onClick={() => irPara(mesSeguinte(mes))}>
            ›
          </button>
          {mes !== mesAtual() && (
            <button type="button" className="link" onClick={() => irPara(mesAtual())}>
              voltar para o mês atual
            </button>
          )}
        </div>

        {secao === "caixa" && (
        <div className="fin-totais">
          <div className="fin-total entrada">
            <span className="fin-rotulo">Entradas</span>
            <strong>R$ {centavosParaBR(caixa.entradasCentavos)}</strong>
          </div>
          <div className="fin-total saida">
            <span className="fin-rotulo">Saídas</span>
            <strong>R$ {centavosParaBR(caixa.saidasCentavos)}</strong>
          </div>
          <div className={caixa.saldoCentavos < 0 ? "fin-total saldo negativo" : "fin-total saldo"}>
            <span className="fin-rotulo">Saldo</span>
            <strong>R$ {centavosParaBR(caixa.saldoCentavos)}</strong>
          </div>
        </div>
        )}
      </div>

      {secao === "mensalidades" && (
        <Mensalidades
          clinic={clinic}
          mes={mes}
          aoMexerNoCaixa={() => setRecarga((n) => n + 1)}
        />
      )}

      {secao === "caixa" && (
      <div className="card">
        <h3>Novo lançamento</h3>
        <div className="fin-form">
          <div className="fin-tipo">
            <button
              type="button"
              className={form.tipo === "entrada" ? "btn tipo on entrada" : "btn tipo"}
              onClick={() => setCampo("tipo", "entrada")}
            >
              Entrada
            </button>
            <button
              type="button"
              className={form.tipo === "saida" ? "btn tipo on saida" : "btn tipo"}
              onClick={() => setCampo("tipo", "saida")}
            >
              Saída
            </button>
          </div>

          <label className="fin-campo">
            <span>Data</span>
            <input type="date" value={form.data} onChange={(e) => setCampo("data", e.target.value)} />
          </label>

          <label className="fin-campo">
            <span>Valor</span>
            <input
              inputMode="numeric"
              placeholder="0,00"
              value={form.valor}
              onChange={(e) => setCampo("valor", maskMoeda(e.target.value))}
            />
          </label>

          <label className="fin-campo cresce">
            <span>Descrição</span>
            <input
              maxLength={200}
              placeholder="Ex.: Conta de luz, mensalidade da Rebecca…"
              value={form.descricao}
              onChange={(e) => setCampo("descricao", e.target.value)}
            />
          </label>

          <label className="fin-campo">
            <span>Forma</span>
            <select
              value={form.formaPagamento}
              onChange={(e) => setCampo("formaPagamento", e.target.value)}
            >
              {FORMAS_PAGAMENTO.map((f) => (
                <option key={f.v} value={f.v}>
                  {f.label}
                </option>
              ))}
            </select>
          </label>

          <button type="button" className="btn primary" disabled={salvando} onClick={salvar}>
            {salvando ? "Salvando…" : "Lançar"}
          </button>
        </div>
      </div>
      )}

      {secao === "caixa" && (
      <div className="card">
        <h3>Extrato</h3>
        {carregando ? (
          <div className="loading">
            <span className="spinner" />
            Carregando o caixa…
          </div>
        ) : vazio ? (
          <p className="muted">
            Nenhum lançamento em {formatMesBR(mes)}. Registre a primeira entrada ou saída no
            formulário acima.
          </p>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Descrição</th>
                  <th>Forma</th>
                  <th className="num">Valor</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {caixa.lancamentos.map((l) => (
                  <tr key={l.id}>
                    <td>{formatDataBR(l.data)}</td>
                    <td>{l.descricao}</td>
                    <td>{labelForma(l.formaPagamento)}</td>
                    <td className={l.tipo === "entrada" ? "num valor entrada" : "num valor saida"}>
                      {l.tipo === "entrada" ? "+" : "−"} R$ {centavosParaBR(l.valorCentavos)}
                    </td>
                    <td className="td-actions">
                      <button type="button" className="link danger" onClick={() => cancelar(l)}>
                        cancelar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      )}
        </>
      )}
    </div>
  );
}
