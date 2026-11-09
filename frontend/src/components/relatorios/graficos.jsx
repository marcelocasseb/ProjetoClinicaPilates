import { useState } from "react";
import { mesCurto, mesLongo } from "./formato";

// Peças de gráfico dos Relatórios — SVG/CSS próprios, sem biblioteca (o front só
// depende de React e o PDF sai pela impressão do navegador).
//
// Regras seguidas (skill dataviz): cor entra por série, em ordem fixa (bronze, azul;
// validadas para daltonismo contra o fundo branco); texto nunca usa a cor da série;
// colunas finas (≤ 24px) com ponta arredondada e base reta; legenda sempre que há 2+
// séries; valor de cada barra também escrito (tooltip ou rótulo) — o gráfico continua
// legível em impressão preto e branco. `null` = "sem dados" (ex.: Agenda expirada),
// desenhado diferente de zero.

// Passo "redondo" para o eixo (1, 2, 2,5, 5 × 10^n) com ~4 divisões.
function ticksRedondos(max) {
  if (!max || max <= 0) return [0, 1];
  const bruto = max / 4;
  const pot = 10 ** Math.floor(Math.log10(bruto));
  const passo = [1, 2, 2.5, 5, 10].map((f) => f * pot).find((p) => p >= bruto);
  const ticks = [];
  for (let v = 0; v <= max + passo * 0.001; v += passo) ticks.push(v);
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + passo);
  return ticks;
}

// Coluna com ponta de 4px arredondada e base reta.
function caminhoColuna(x, y, w, h) {
  const r = Math.min(4, h, w / 2);
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`;
}

export function Legenda({ series }) {
  if (series.length < 2) return null;
  return (
    <ul className="rel-legenda">
      {series.map((s) => (
        <li key={s.chave}>
          <span className="rel-legenda-cor" style={{ background: s.cor }} aria-hidden="true" />
          {s.nome}
        </li>
      ))}
    </ul>
  );
}

/**
 * Colunas mensais (12 meses), agrupadas por série.
 * dados: [{ mes: "2026-10", [chave]: number|null }]
 * series: [{ chave, nome, cor }]
 * formato: valor → texto completo (tooltip); formatoEixo: valor → texto curto (eixo)
 */
export function BarrasMensais({ dados, series, formato = String, formatoEixo = formato, rotulo }) {
  const [foco, setFoco] = useState(null);
  const W = 640;
  const H = 220;
  const M = { t: 12, r: 8, b: 34, l: 64 };
  const plotW = W - M.l - M.r;
  const plotH = H - M.t - M.b;
  const max = Math.max(0, ...dados.flatMap((d) => series.map((s) => d[s.chave] ?? 0)));
  const ticks = ticksRedondos(max);
  const topo = ticks[ticks.length - 1] || 1;
  const banda = plotW / Math.max(1, dados.length);
  const GAP = 2;
  const barW = Math.min(24, (banda * 0.72 - GAP * (series.length - 1)) / series.length);
  const grupoW = barW * series.length + GAP * (series.length - 1);
  const y = (v) => M.t + plotH - (v / topo) * plotH;

  const ativo = foco != null ? dados[foco] : null;
  const xTooltip = foco != null ? ((M.l + banda * foco + banda / 2) / W) * 100 : 0;

  return (
    <div className="rel-grafico">
      <Legenda series={series} />
      <div className="rel-grafico-rolagem">
        <div className="rel-grafico-area">
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={rotulo} className="rel-svg">
            {ticks.map((t) => (
              <g key={t}>
                <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} className={t === 0 ? "rel-base" : "rel-grade"} />
                <text x={M.l - 8} y={y(t)} dy="0.32em" textAnchor="end" className="rel-eixo">
                  {formatoEixo(t)}
                </text>
              </g>
            ))}
            {dados.map((d, i) => {
              const x0 = M.l + banda * i + (banda - grupoW) / 2;
              const anoNovo = i === 0 || d.mes.endsWith("-01");
              return (
                <g key={d.mes}>
                  {series.map((s, j) => {
                    const v = d[s.chave];
                    const x = x0 + j * (barW + GAP);
                    if (v == null) {
                      return (
                        <text key={s.chave} x={x + barW / 2} y={y(0) - 4} textAnchor="middle" className="rel-sd">
                          s/d
                        </text>
                      );
                    }
                    const h = Math.max(0, y(0) - y(v));
                    return h > 0 ? (
                      <path key={s.chave} d={caminhoColuna(x, y(v), barW, h)} fill={s.cor} className={foco === i ? "rel-marca on" : "rel-marca"} />
                    ) : null;
                  })}
                  <text x={M.l + banda * i + banda / 2} y={H - M.b + 16} textAnchor="middle" className="rel-eixo">
                    {mesCurto(d.mes)}
                  </text>
                  {anoNovo && (
                    <text x={M.l + banda * i + banda / 2} y={H - M.b + 29} textAnchor="middle" className="rel-eixo rel-ano">
                      {d.mes.slice(0, 4)}
                    </text>
                  )}
                  {/* alvo do mouse/teclado: a faixa inteira do mês, maior que a barra */}
                  <rect
                    x={M.l + banda * i}
                    y={M.t}
                    width={banda}
                    height={plotH}
                    fill="transparent"
                    tabIndex={0}
                    aria-label={`${mesLongo(d.mes)}: ${series.map((s) => `${s.nome} ${d[s.chave] == null ? "sem dados" : formato(d[s.chave])}`).join(", ")}`}
                    onPointerEnter={() => setFoco(i)}
                    onPointerLeave={() => setFoco(null)}
                    onFocus={() => setFoco(i)}
                    onBlur={() => setFoco(null)}
                  />
                </g>
              );
            })}
          </svg>
          {ativo && (
            <div className="rel-tooltip" style={{ left: `${Math.min(80, Math.max(20, xTooltip))}%` }} role="status">
              <div className="rel-tooltip-titulo">{mesLongo(ativo.mes)}</div>
              {series.map((s) => (
                <div key={s.chave} className="rel-tooltip-linha">
                  <span className="rel-tooltip-key" style={{ background: s.cor }} aria-hidden="true" />
                  <strong>{ativo[s.chave] == null ? "sem dados" : formato(ativo[s.chave])}</strong>
                  <span>{s.nome}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Ranking em barras horizontais (uma série). itens: [{ nome, valor }].
 * O valor fica escrito na ponta de cada barra.
 */
export function Ranking({ itens, formato = String, cor = "var(--serie-1)", vazio = "Sem dados." }) {
  if (!itens.length) return <p className="muted rel-vazio">{vazio}</p>;
  const max = Math.max(...itens.map((i) => i.valor), 1);
  return (
    <ol className="rel-ranking">
      {itens.map((i) => (
        <li key={i.nome}>
          <span className="rel-ranking-nome" title={i.nome}>{i.nome}</span>
          <span className="rel-ranking-trilho">
            <span className="rel-ranking-barra" style={{ width: `${(i.valor / max) * 100}%`, background: cor }} />
          </span>
          <span className="rel-ranking-valor">{formato(i.valor, i)}</span>
        </li>
      ))}
    </ol>
  );
}

// Rampa sequencial em um só tom (bronze da marca), do claro ao escuro.
// Nos 3 primeiros degraus o número vai em tinta escura; nos 2 últimos, em branco.
const RAMPA = ["#f5ead7", "#e8cfa3", "#d4ac6c", "#b07a2a", "#7d5418"];

/**
 * Mapa de calor dia × horário. celulas: [{ dia, hora, alunos }].
 * dias: [{ n, curto, nome }]; horarios: ["06:00", …].
 */
export function MapaCalor({ celulas, dias, horarios }) {
  const valor = new Map(celulas.map((c) => [`${c.dia}|${c.hora}`, c.alunos]));
  const max = Math.max(1, ...celulas.map((c) => c.alunos));
  const linhas = [...new Set([...horarios, ...celulas.map((c) => c.hora)])].sort();
  const degrau = (v) => Math.min(RAMPA.length - 1, Math.ceil((v / max) * RAMPA.length) - 1);
  const faixas = RAMPA.map((_, k) => {
    const de = Math.floor((k * max) / RAMPA.length) + 1;
    const ate = Math.ceil(((k + 1) * max) / RAMPA.length);
    return de > ate ? null : de === ate ? `${de}` : `${de}–${ate}`;
  });
  return (
    <div className="rel-calor">
      <div className="rel-grafico-rolagem">
        <table className="rel-calor-tabela">
          <thead>
            <tr>
              <th scope="col">Horário</th>
              {dias.map((d) => (
                <th key={d.n} scope="col" title={d.nome}>{d.curto}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map((h) => (
              <tr key={h}>
                <th scope="row">{h}</th>
                {dias.map((d) => {
                  const v = valor.get(`${d.n}|${h}`) || 0;
                  const k = v ? degrau(v) : -1;
                  return (
                    <td
                      key={d.n}
                      className={k >= 3 ? "rel-calor-cel escura" : "rel-calor-cel"}
                      style={k >= 0 ? { background: RAMPA[k] } : undefined}
                      title={`${d.nome} ${h}: ${v} ${v === 1 ? "aluno" : "alunos"}`}
                    >
                      {v || ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="rel-calor-legenda" aria-label="Legenda: quanto mais escuro, mais alunos">
        <span className="muted">Alunos por horário:</span>
        {RAMPA.map((c, k) =>
          faixas[k] ? (
            <span key={c} className="rel-calor-faixa">
              <span className="rel-legenda-cor" style={{ background: c }} aria-hidden="true" />
              {faixas[k]}
            </span>
          ) : null,
        )}
      </div>
    </div>
  );
}

/** Cartão de número: rótulo, valor e (opcional) detalhe. */
export function Kpi({ rotulo, valor, detalhe, tom }) {
  return (
    <div className={tom ? `rel-kpi ${tom}` : "rel-kpi"}>
      <span className="rel-kpi-rotulo">{rotulo}</span>
      <strong className="rel-kpi-valor">{valor}</strong>
      {detalhe ? <span className="rel-kpi-detalhe">{detalhe}</span> : null}
    </div>
  );
}
