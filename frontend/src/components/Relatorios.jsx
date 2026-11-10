import { useCallback, useEffect, useRef, useState } from "react";
import { relatoriosApi } from "../api";
import { formatMesBR, hojeISO, mesAnterior, mesAtual, mesSeguinte } from "../utils/format";
import { dataBR } from "./relatorios/formato";
import RelAlunos from "./relatorios/RelAlunos";
import RelAtendimento from "./relatorios/RelAtendimento";
import RelFinanceiro from "./relatorios/RelFinanceiro";
import RelOcupacao from "./relatorios/RelOcupacao";
import RelRelacaoAlunos from "./relatorios/RelRelacaoAlunos";
import RelSemana from "./relatorios/RelSemana";

// Aba Relatórios (só admin — REL-01). Container: escolhe o relatório e o período,
// busca os dados (já somados no back) e entrega a componentes de apresentação puros.
// Os mesmos componentes montam o PDF de um relatório e o fechamento, então os números
// da tela, do PDF e do fechamento são sempre os mesmos.
//
// PDF = impressão do navegador (`window.print()` + `@media print` no App.css): sem
// biblioteca nova; o usuário escolhe "Salvar como PDF" no destino.

const GRUPOS = [
  { id: "financeiro", nome: "Financeiro" },
  { id: "alunos", nome: "Alunos" },
  { id: "ocupacao", nome: "Ocupação" },
  { id: "atendimento", nome: "Atendimento" },
  { id: "semana", nome: "Semana" },
];

const TITULOS = {
  financeiro: "Relatório financeiro",
  alunos: "Alunos",
  relacao: "Relação de alunos",
  ocupacao: "Ocupação da escala",
  atendimento: "Atendimento",
  semana: "Quem passou na semana",
};

// Datas em "AAAA-MM-DD", contadas no calendário (sem fuso no meio).
function somaDias(iso, n) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(a, m - 1, d + n)).toISOString().slice(0, 10);
}
function segundaDe(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  const dow = (new Date(Date.UTC(a, m - 1, d)).getUTCDay() + 6) % 7; // 0 = segunda
  return somaDias(iso, -dow);
}
const textoSemana = (seg) => `Semana de ${dataBR(seg).slice(0, 5)} a ${dataBR(somaDias(seg, 6))}`;

// Período (REL-23): { mes } = mês inteiro (navegável com ‹ ›) ou { de, ate } = intervalo.
const textoPeriodo = (p) => (p.mes ? formatMesBR(p.mes) : `${dataBR(p.de)} a ${dataBR(p.ate)}`);

const ATALHOS = [
  { id: "este-mes", nome: "Este mês", periodo: () => ({ mes: mesAtual() }) },
  { id: "mes-passado", nome: "Mês passado", periodo: () => ({ mes: mesAnterior(mesAtual()) }) },
  { id: "7d", nome: "Últimos 7 dias", periodo: () => ({ de: somaDias(hojeISO(), -6), ate: hojeISO() }) },
  { id: "30d", nome: "Últimos 30 dias", periodo: () => ({ de: somaDias(hojeISO(), -29), ate: hojeISO() }) },
  { id: "ano", nome: "Este ano", periodo: () => ({ de: `${hojeISO().slice(0, 4)}-01-01`, ate: hojeISO() }) },
];

export function CabecalhoImpressao({ clinicaNome, titulo, referencia }) {
  return (
    <header className="rel-cabecalho-impressao">
      <div>
        <strong>{clinicaNome || "Pilates One"}</strong>
        <span>{titulo}</span>
      </div>
      <div className="rel-cabecalho-dir">
        <span>{referencia}</span>
        <span>Emitido em {new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</span>
      </div>
    </header>
  );
}

function buscar(vista, periodo, semana) {
  switch (vista) {
    case "financeiro":
      return relatoriosApi.financeiro(periodo);
    case "alunos":
      return relatoriosApi.alunos(periodo);
    case "relacao":
      return relatoriosApi.relacaoAlunos();
    case "ocupacao":
      return relatoriosApi.ocupacao();
    case "atendimento":
      return relatoriosApi.atendimento(periodo);
    default:
      return relatoriosApi.semana(semana);
  }
}

function Conteudo({ vista, dados }) {
  switch (vista) {
    case "financeiro":
      return <RelFinanceiro dados={dados} />;
    case "alunos":
      return <RelAlunos dados={dados} />;
    case "relacao":
      return <RelRelacaoAlunos dados={dados} />;
    case "ocupacao":
      return <RelOcupacao dados={dados} />;
    case "atendimento":
      return <RelAtendimento dados={dados} />;
    default:
      return <RelSemana dados={dados} />;
  }
}

// Fechamento (REL-17): os 4 grupos do período, cada um numa página.
const PARTES_FECHAMENTO = [
  { vista: "financeiro", nome: "Financeiro" },
  { vista: "alunos", nome: "Alunos" },
  { vista: "ocupacao", nome: "Ocupação" },
  { vista: "atendimento", nome: "Atendimento" },
];

function SeletorPeriodo({ periodo, atalho, onEscolher }) {
  const [aberto, setAberto] = useState(atalho === "personalizado");
  const [de, setDe] = useState(periodo.de || `${periodo.mes}-01`);
  const [ate, setAte] = useState(periodo.ate || hojeISO());
  const hoje = hojeISO();
  const invalido = !de || !ate || de > ate || ate > hoje;

  return (
    <div className="rel-periodo">
      <div className="rel-atalhos" role="group" aria-label="Período">
        {ATALHOS.map((a) => (
          <button
            key={a.id}
            className={atalho === a.id ? "rel-chip on" : "rel-chip"}
            onClick={() => {
              setAberto(false);
              onEscolher(a.periodo(), a.id);
            }}
          >
            {a.nome}
          </button>
        ))}
        <button
          className={atalho === "personalizado" || aberto ? "rel-chip on" : "rel-chip"}
          onClick={() => setAberto((v) => !v)}
          aria-expanded={aberto}
        >
          Personalizado
        </button>
      </div>

      {periodo.mes && !aberto && (
        <div className="fin-mes rel-nav">
          <button
            className="btn ghost"
            onClick={() => onEscolher({ mes: mesAnterior(periodo.mes) }, "mes")}
            aria-label="Mês anterior"
          >
            ‹
          </button>
          <strong>{formatMesBR(periodo.mes)}</strong>
          <button
            className="btn ghost"
            onClick={() => onEscolher({ mes: mesSeguinte(periodo.mes) }, "mes")}
            disabled={periodo.mes >= mesAtual()}
            aria-label="Próximo mês"
          >
            ›
          </button>
        </div>
      )}
      {!periodo.mes && !aberto && <strong className="rel-periodo-texto">{textoPeriodo(periodo)}</strong>}

      {aberto && (
        <form
          className="rel-personalizado"
          onSubmit={(e) => {
            e.preventDefault();
            if (!invalido) onEscolher({ de, ate }, "personalizado");
          }}
        >
          <label>
            De
            <input type="date" value={de} max={hoje} onChange={(e) => setDe(e.target.value)} required />
          </label>
          <label>
            Até
            <input type="date" value={ate} max={hoje} onChange={(e) => setAte(e.target.value)} required />
          </label>
          <button type="submit" className="btn primary" disabled={invalido}>
            Aplicar
          </button>
          {de > ate && <span className="erro">A data inicial é depois da final.</span>}
        </form>
      )}
    </div>
  );
}

export default function Relatorios({ clinicaNome }) {
  const [grupo, setGrupo] = useState("financeiro");
  const [subAlunos, setSubAlunos] = useState("indicadores");
  const [periodo, setPeriodo] = useState(() => ({ mes: mesAtual() }));
  const [atalho, setAtalho] = useState("este-mes");
  const [semana, setSemana] = useState(() => segundaDe(hojeISO()));
  const [dados, setDados] = useState(null);
  const [dadosVista, setDadosVista] = useState(null); // de qual vista são os `dados`
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [recarga, setRecarga] = useState(0);
  const [fechamento, setFechamento] = useState(null); // { carregando } | { dados } | null
  const [erroFechamento, setErroFechamento] = useState("");
  const pedido = useRef(0);

  const vista = grupo === "alunos" && subAlunos === "relacao" ? "relacao" : grupo;
  const usaPeriodo = ["financeiro", "alunos", "atendimento"].includes(vista);
  const usaSemana = vista === "semana";
  const semanaHoje = segundaDe(hojeISO());
  const chavePeriodo = JSON.stringify(periodo);

  useEffect(() => {
    const id = ++pedido.current;
    setCarregando(true);
    setErro("");
    buscar(vista, JSON.parse(chavePeriodo), semana)
      .then((r) => {
        if (id !== pedido.current) return; // resposta antiga: ignora
        setDados(r);
        setDadosVista(vista);
      })
      .catch((e) => id === pedido.current && setErro(e.message || "Não foi possível carregar o relatório."))
      .finally(() => id === pedido.current && setCarregando(false));
  }, [vista, chavePeriodo, semana, recarga]);

  const imprimir = useCallback(() => window.print(), []);

  function escolherPeriodo(p, id) {
    setPeriodo(p);
    // ‹ › num mês volta a ser "mês" (deixa de ser "Este mês"/"Mês passado").
    if (id === "mes") setAtalho(p.mes === mesAtual() ? "este-mes" : p.mes === mesAnterior(mesAtual()) ? "mes-passado" : "mes");
    else setAtalho(id);
  }

  async function gerarFechamento() {
    setErroFechamento("");
    setFechamento({ carregando: true });
    const resultados = await Promise.allSettled(PARTES_FECHAMENTO.map((p) => buscar(p.vista, periodo, semana)));
    const falhas = PARTES_FECHAMENTO.filter((_, i) => resultados[i].status === "rejected").map((p) => p.nome);
    if (falhas.length) {
      // REL-17 AC4: nunca imprimir um fechamento incompleto em silêncio.
      setFechamento(null);
      setErroFechamento(`O fechamento não foi gerado: falhou ${falhas.join(", ")}. Tente de novo.`);
      return;
    }
    setFechamento({ dados: resultados.map((r) => r.value) });
  }

  // Com o fechamento montado, imprime no próximo quadro e desmonta ao fechar a impressão.
  useEffect(() => {
    if (!fechamento?.dados) return undefined;
    const fim = () => setFechamento(null);
    window.addEventListener("afterprint", fim);
    const raf = requestAnimationFrame(() => window.print());
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("afterprint", fim);
    };
  }, [fechamento]);

  const posicaoHoje = `Posição em ${dataBR(hojeISO())}`;
  const referencia = usaPeriodo ? textoPeriodo(periodo) : usaSemana ? textoSemana(semana) : posicaoHoje;
  const prontos = dados && dadosVista === vista;

  return (
    <div className={fechamento?.dados ? "rel-root imprimindo-fechamento" : "rel-root"}>
      <div className="rel-tela">
        <div className="card rel-topo no-print">
          <div className="rel-topo-linha">
            <h2>Relatórios</h2>
            <div className="rel-acoes">
              <button className="btn ghost" onClick={imprimir} disabled={!prontos || carregando}>
                Imprimir / PDF
              </button>
              <button className="btn primary" onClick={gerarFechamento} disabled={fechamento?.carregando}>
                {fechamento?.carregando ? "Preparando…" : `Fechamento · ${textoPeriodo(periodo)}`}
              </button>
            </div>
          </div>
          <p className="muted rel-dica">
            Para salvar em PDF, escolha <strong>Salvar como PDF</strong> no destino da impressão.
          </p>
          {erroFechamento && <div className="erro">{erroFechamento}</div>}

          <div className="rel-subabas" role="tablist">
            {GRUPOS.map((g) => (
              <button
                key={g.id}
                role="tab"
                aria-selected={grupo === g.id}
                className={grupo === g.id ? "rel-subaba on" : "rel-subaba"}
                onClick={() => setGrupo(g.id)}
              >
                {g.nome}
              </button>
            ))}
          </div>

          <div className="rel-filtros">
            {grupo === "alunos" && (
              <div className="rel-seg" role="group" aria-label="Visão de alunos">
                <button className={subAlunos === "indicadores" ? "on" : ""} onClick={() => setSubAlunos("indicadores")}>
                  Indicadores
                </button>
                <button className={subAlunos === "relacao" ? "on" : ""} onClick={() => setSubAlunos("relacao")}>
                  Relação de alunos
                </button>
              </div>
            )}
            {usaPeriodo && (
              <SeletorPeriodo key={chavePeriodo} periodo={periodo} atalho={atalho} onEscolher={escolherPeriodo} />
            )}
            {usaSemana && (
              <div className="fin-mes rel-nav">
                <button className="btn ghost" onClick={() => setSemana(somaDias(semana, -7))} aria-label="Semana anterior">
                  ‹
                </button>
                <strong>{textoSemana(semana)}</strong>
                <button
                  className="btn ghost"
                  onClick={() => setSemana(somaDias(semana, 7))}
                  disabled={semana >= semanaHoje}
                  aria-label="Próxima semana"
                >
                  ›
                </button>
              </div>
            )}
          </div>
        </div>

        <div className={carregando && prontos ? "card rel-corpo recarregando" : "card rel-corpo"}>
          <CabecalhoImpressao clinicaNome={clinicaNome} titulo={TITULOS[vista]} referencia={referencia} />
          <h2 className="rel-titulo">
            {TITULOS[vista]} <span className="muted">· {referencia}</span>
          </h2>
          {erro ? (
            <div className="rel-erro">
              <p className="erro">Não foi possível carregar o relatório: {erro}</p>
              <button className="btn ghost" onClick={() => setRecarga((n) => n + 1)}>
                Tentar de novo
              </button>
            </div>
          ) : prontos ? (
            <Conteudo vista={vista} dados={dados} />
          ) : (
            <p className="muted rel-vazio">Carregando…</p>
          )}
        </div>
      </div>

      {fechamento?.dados && (
        <div className="rel-fechamento" aria-hidden="true">
          <section className="rel-capa">
            <span className="rel-capa-marca">{clinicaNome || "Pilates One"}</span>
            <h1>Fechamento</h1>
            <p>{textoPeriodo(periodo)}</p>
            <p className="rel-capa-emissao">
              Emitido em {new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
            </p>
            <ol>
              {PARTES_FECHAMENTO.map((p) => (
                <li key={p.vista}>{TITULOS[p.vista]}</li>
              ))}
            </ol>
          </section>
          {PARTES_FECHAMENTO.map((p, i) => (
            <section key={p.vista} className="rel-secao">
              <CabecalhoImpressao
                clinicaNome={clinicaNome}
                titulo={TITULOS[p.vista]}
                referencia={p.vista === "ocupacao" ? posicaoHoje : textoPeriodo(periodo)}
              />
              <h2 className="rel-titulo">{TITULOS[p.vista]}</h2>
              <Conteudo vista={p.vista} dados={fechamento.dados[i]} />
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
