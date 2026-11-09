import { useState } from "react";
import { BarrasMensais, Kpi, Ranking } from "./graficos";
import { dataLocal, inteiro, mesLongo, plural, reais, SERIE_1 } from "./formato";

const SERIES = [{ chave: "ativos", nome: "Alunos ativos", cor: SERIE_1 }];

// Relatório de Alunos (REL-07..10): indicadores do mês, evolução e carteira de planos.
export default function RelAlunos({ dados }) {
  const [verTabela, setVerTabela] = useState(false);
  const c = dados.carteira;

  return (
    <div className="rel-relatorio">
      <div className="rel-kpis">
        <Kpi rotulo="Ativos no fim do mês" valor={inteiro(dados.ativosFimMes)} tom="destaque" />
        <Kpi rotulo="Novos no mês" valor={inteiro(dados.novos)} />
        <Kpi rotulo="Saídas no mês" valor={inteiro(dados.saidas)} />
        <Kpi rotulo="Planos por mês" valor={reais(c.totalMensalCentavos)} detalhe="soma dos planos ativos hoje" />
      </div>

      <section className="rel-bloco">
        <div className="rel-bloco-topo">
          <h3>Alunos ativos nos últimos 12 meses</h3>
          <button className="btn ghost rel-mini no-print" onClick={() => setVerTabela((v) => !v)}>
            {verTabela ? "Ocultar tabela" : "Ver tabela"}
          </button>
        </div>
        <BarrasMensais
          dados={dados.evolucao}
          series={SERIES}
          formato={(v) => plural(v, "aluno", "alunos")}
          formatoEixo={inteiro}
          rotulo="Alunos ativos no fim de cada mês"
        />
        <table className={verTabela ? "rel-tabela" : "rel-tabela so-impressao"}>
          <thead>
            <tr>
              <th>Mês</th>
              <th className="num">Ativos</th>
              <th className="num">Novos</th>
              <th className="num">Saídas</th>
            </tr>
          </thead>
          <tbody>
            {dados.evolucao.map((m) => (
              <tr key={m.mes}>
                <td>{mesLongo(m.mes)}</td>
                <td className="num">{inteiro(m.ativos)}</td>
                <td className="num">{inteiro(m.novos)}</td>
                <td className="num">{inteiro(m.saidas)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="rel-colunas">
        <section className="rel-bloco">
          <h3>Carteira de planos</h3>
          <dl className="rel-lista-valores">
            <div><dt>Ticket médio</dt><dd>{reais(c.ticketMedioCentavos)}</dd></div>
            <div><dt>Com plano pago</dt><dd>{plural(c.comPlano, "aluno", "alunos")}</dd></div>
            <div><dt>Isentos</dt><dd>{plural(c.isentos, "aluno", "alunos")}</dd></div>
            <div><dt>Sem plano</dt><dd>{plural(c.semPlano, "aluno", "alunos")}</dd></div>
          </dl>
          <h4>Frequência dos planos</h4>
          <Ranking
            itens={c.porFrequencia.map((f) => ({
              nome: f.frequencia ? `${f.frequencia}x por semana` : "Frequência não informada",
              valor: f.alunos,
            }))}
            formato={(v) => plural(v, "aluno", "alunos")}
            vazio="Nenhum plano cadastrado."
          />
          <p className="rel-nota">O ticket médio não conta os isentos (bolsistas e cortesias).</p>
        </section>

        <section className="rel-bloco">
          <h3>Alunos novos no mês</h3>
          {dados.novosLista.length === 0 ? (
            <p className="muted rel-vazio">Nenhum aluno cadastrado neste mês.</p>
          ) : (
            <table className="rel-tabela">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Cadastro</th>
                </tr>
              </thead>
              <tbody>
                {dados.novosLista.map((a) => (
                  <tr key={a.id}>
                    <td>{a.nome}</td>
                    <td>{dataLocal(a.criadoEm)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
