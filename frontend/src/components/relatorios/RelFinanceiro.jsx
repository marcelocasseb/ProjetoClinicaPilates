import { useState } from "react";
import { formatDataBR } from "../../utils/format";
import { BarrasMensais, Kpi, Ranking } from "./graficos";
import { mesLongo, nomeForma, plural, reais, reaisCurto, SERIE_1, SERIE_2 } from "./formato";

const SERIES = [
  { chave: "entradasCentavos", nome: "Entradas", cor: SERIE_1 },
  { chave: "saidasCentavos", nome: "Saídas", cor: SERIE_2 },
];

const STATUS = [
  ["pago", "Pagos"],
  ["parcial", "Parciais"],
  ["aberto", "Em aberto"],
  ["isento", "Isentos"],
  ["sem_plano", "Sem plano"],
];

// Relatório Financeiro (REL-03..06, REL-20): apresentação pura dos dados do back.
export default function RelFinanceiro({ dados }) {
  const [verTabela, setVerTabela] = useState(false);
  const { caixa, mensalidades: men } = dados;
  const entradas = dados.extrato.filter((l) => l.tipo === "entrada");
  const saidas = dados.extrato.filter((l) => l.tipo !== "entrada");

  return (
    <div className="rel-relatorio">
      <div className="rel-kpis">
        <Kpi rotulo="Entradas" valor={reais(caixa.entradasCentavos)} />
        <Kpi rotulo="Saídas" valor={reais(caixa.saidasCentavos)} />
        <Kpi
          rotulo="Saldo do mês"
          valor={reais(caixa.saldoCentavos)}
          tom={caixa.saldoCentavos < 0 ? "negativo" : "destaque"}
        />
        <Kpi
          rotulo="Mensalidades em aberto"
          valor={reais(men.emAbertoCentavos)}
          detalhe={`de ${reais(men.previstoCentavos)} previstos`}
        />
      </div>

      <section className="rel-bloco">
        <div className="rel-bloco-topo">
          <h3>Entradas e saídas nos últimos 12 meses</h3>
          <button className="btn ghost rel-mini no-print" onClick={() => setVerTabela((v) => !v)}>
            {verTabela ? "Ocultar tabela" : "Ver tabela"}
          </button>
        </div>
        <BarrasMensais
          dados={dados.evolucao}
          series={SERIES}
          formato={reais}
          formatoEixo={reaisCurto}
          rotulo="Entradas e saídas por mês"
        />
        <table className={verTabela ? "rel-tabela" : "rel-tabela so-impressao"}>
          <thead>
            <tr>
              <th>Mês</th>
              <th className="num">Entradas</th>
              <th className="num">Saídas</th>
              <th className="num">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {dados.evolucao.map((m) => (
              <tr key={m.mes}>
                <td>{mesLongo(m.mes)}</td>
                <td className="num">{reais(m.entradasCentavos)}</td>
                <td className="num">{reais(m.saidasCentavos)}</td>
                <td className={m.saldoCentavos < 0 ? "num negativo" : "num"}>{reais(m.saldoCentavos)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="rel-colunas">
        <section className="rel-bloco">
          <h3>Receita por forma de pagamento</h3>
          <Ranking
            itens={dados.porForma.map((f) => ({ nome: nomeForma(f.forma), valor: f.valorCentavos, pct: f.pct }))}
            formato={(v, i) => `${reais(v)} · ${String(i.pct).replace(".", ",")}%`}
            vazio="Nenhuma entrada neste mês."
          />
        </section>

        <section className="rel-bloco">
          <h3>Mensalidades do mês</h3>
          <dl className="rel-lista-valores">
            <div><dt>Previsto</dt><dd>{reais(men.previstoCentavos)}</dd></div>
            <div><dt>Recebido</dt><dd>{reais(men.recebidoCentavos)}</dd></div>
            <div><dt>Em aberto</dt><dd>{reais(men.emAbertoCentavos)}</dd></div>
          </dl>
          <ul className="rel-status">
            {STATUS.map(([k, nome]) => (
              <li key={k}>
                <span>{nome}</span>
                <strong>{plural(men.porStatus[k] || 0, "aluno", "alunos")}</strong>
              </li>
            ))}
          </ul>
          <p className="rel-nota">Usa os planos e os alunos ativos de hoje, como a tela Mensalidades.</p>
        </section>
      </div>

      <section className="rel-bloco rel-quebra-antes">
        <h3>Extrato do mês</h3>
        {dados.extrato.length === 0 ? (
          <p className="muted rel-vazio">Nenhum lançamento neste mês.</p>
        ) : (
          <table className="rel-tabela">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Forma</th>
                <th className="num">Entrada</th>
                <th className="num">Saída</th>
              </tr>
            </thead>
            <tbody>
              {dados.extrato.map((l, i) => (
                <tr key={i}>
                  <td>{formatDataBR(l.data)}</td>
                  <td>{l.descricao}</td>
                  <td>{nomeForma(l.formaPagamento || "nao_informado")}</td>
                  <td className="num">{l.tipo === "entrada" ? reais(l.valorCentavos) : ""}</td>
                  <td className="num">{l.tipo !== "entrada" ? reais(l.valorCentavos) : ""}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}>
                  Totais ({plural(entradas.length, "entrada", "entradas")}, {plural(saidas.length, "saída", "saídas")})
                </td>
                <td className="num">{reais(caixa.entradasCentavos)}</td>
                <td className="num">{reais(caixa.saidasCentavos)}</td>
              </tr>
              <tr>
                <td colSpan={3}>Saldo</td>
                <td colSpan={2} className={caixa.saldoCentavos < 0 ? "num negativo" : "num"}>
                  {reais(caixa.saldoCentavos)}
                </td>
              </tr>
            </tfoot>
          </table>
        )}
      </section>
    </div>
  );
}
