// Tabela de preços da clínica (fluxo-caixa F2).
//
// A clínica digita SÓ o valor MENSAL de cada frequência. O "por aula" ao lado é
// calculado e read-only — ele existe para a dona enxergar se o desconto de volume
// ficou do jeito que ela quer, sem fazer conta no papel.
//
// Preço por aula digitado de verdade existe em um lugar só: aula avulsa e reposição,
// que são de quem NÃO é mensalista.
import { useEffect, useState } from "react";
import { financeiroApi } from "../api";
import { brParaCentavos, centavosParaBR, maskMoeda } from "../utils/format";

// Semanas médias no mês (52/12) — o divisor do "por aula" derivado.
const SEMANAS_NO_MES = 4.33;

const FREQUENCIAS = [1, 2, 3, 4, 5];

export default function TabelaPrecos({ clinic }) {
  const [linhas, setLinhas] = useState({}); // { [frequencia]: "260,00" }
  const [avulsa, setAvulsa] = useState("");
  const [reposicao, setReposicao] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    financeiroApi
      .config(clinic.id)
      .then((cfg) => {
        if (!ativo) return;
        const mapa = {};
        for (const f of cfg.tabelaPrecos || []) mapa[f.frequencia] = centavosParaBR(f.valorCentavos);
        setLinhas(mapa);
        setAvulsa(cfg.aulaAvulsaCentavos ? centavosParaBR(cfg.aulaAvulsaCentavos) : "");
        setReposicao(cfg.reposicaoCentavos ? centavosParaBR(cfg.reposicaoCentavos) : "");
      })
      .catch((e) => ativo && setErro(e.message))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, [clinic.id]);

  async function salvar() {
    setErro("");
    setOk("");
    setSalvando(true);
    try {
      const tabelaPrecos = FREQUENCIAS.filter((f) => brParaCentavos(linhas[f] || "") > 0).map(
        (f) => ({ frequencia: f, valorCentavos: brParaCentavos(linhas[f]) })
      );
      await financeiroApi.salvarConfig(clinic.id, {
        tabelaPrecos,
        aulaAvulsaCentavos: brParaCentavos(avulsa),
        reposicaoCentavos: brParaCentavos(reposicao),
      });
      setOk("Tabela de preços salva.");
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  // Valor por aula = mensal ÷ (aulas por semana × semanas no mês). Dividir só pelas
  // semanas daria o valor da SEMANA, não da aula — e faria um plano 5x parecer o mais
  // caro por aula, que é exatamente o contrário do desconto de volume.
  function porAula(texto, frequencia) {
    const c = brParaCentavos(texto || "");
    if (!c) return "—";
    return `R$ ${centavosParaBR(Math.round(c / (frequencia * SEMANAS_NO_MES)))}`;
  }

  if (carregando) {
    return (
      <div className="card">
        <div className="loading">
          <span className="spinner" />
          Carregando a tabela de preços…
        </div>
      </div>
    );
  }

  return (
    <div>
      {erro && <div className="erro">{erro}</div>}
      {ok && <div className="ok-msg">{ok}</div>}

      <div className="card">
        <h3>Mensalidade por frequência</h3>
        <p className="muted">
          Você digita só o <strong>valor mensal</strong>. O valor por aula ao lado é calculado
          (mensal ÷ aulas no mês, contando {SEMANAS_NO_MES} semanas) e serve para você conferir
          o desconto de volume.
        </p>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Frequência</th>
                <th className="num">Valor mensal</th>
                <th className="num">≈ por aula</th>
              </tr>
            </thead>
            <tbody>
              {FREQUENCIAS.map((f) => (
                <tr key={f}>
                  <td>{f}x por semana</td>
                  <td className="num">
                    <input
                      className="input-valor"
                      inputMode="numeric"
                      placeholder="0,00"
                      value={linhas[f] || ""}
                      onChange={(e) =>
                        setLinhas((l) => ({ ...l, [f]: maskMoeda(e.target.value) }))
                      }
                    />
                  </td>
                  <td className="num muted">{porAula(linhas[f], f)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted">
          Frequência deixada em branco simplesmente não aparece como sugestão. Nada aqui é
          obrigatório — dá para digitar o valor direto no aluno.
        </p>
      </div>

      <div className="card">
        <h3>Preço por aula (quem não é mensalista)</h3>
        <div className="fin-form">
          <label className="fin-campo">
            <span>Aula avulsa</span>
            <input
              inputMode="numeric"
              placeholder="0,00"
              value={avulsa}
              onChange={(e) => setAvulsa(maskMoeda(e.target.value))}
            />
          </label>
          <label className="fin-campo">
            <span>Reposição</span>
            <input
              inputMode="numeric"
              placeholder="0,00"
              value={reposicao}
              onChange={(e) => setReposicao(maskMoeda(e.target.value))}
            />
          </label>
          <span className="muted">Reposição 0,00 = cortesia.</span>
        </div>
      </div>

      <div className="card">
        <button type="button" className="btn primary" disabled={salvando} onClick={salvar}>
          {salvando ? "Salvando…" : "Salvar tabela de preços"}
        </button>
      </div>
    </div>
  );
}
