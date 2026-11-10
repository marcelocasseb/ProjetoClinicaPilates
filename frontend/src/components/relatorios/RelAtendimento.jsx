import { useState } from "react";
import { BarrasMensais, Kpi, Ranking } from "./graficos";
import { inteiro, mesLongo, NOTA_MESES_INTEIROS, periodoParcial, plural, SERIE_1, SERIE_2 } from "./formato";

const SERIES = [
  { chave: "aulas", nome: "Aulas registradas", cor: SERIE_1 },
  { chave: "agenda", nome: "Marcações na Agenda", cor: SERIE_2 },
];

const n = (v) => (v == null ? "s/d" : inteiro(v));

function TabelaFontes({ linhas, rotulo, vazio }) {
  if (!linhas.length) return <p className="muted rel-vazio">{vazio}</p>;
  return (
    <table className="rel-tabela">
      <thead>
        <tr>
          <th>{rotulo}</th>
          <th className="num">Aulas registradas</th>
          <th className="num">Marcações na Agenda</th>
        </tr>
      </thead>
      <tbody>
        {linhas.map((l, i) => (
          <tr key={i}>
            <td>
              {l.nome || "—"}
              {l.novo ? <span className="rel-tag">novo</span> : null}
            </td>
            <td className="num">{n(l.aulas)}</td>
            <td className="num">{n(l.agenda)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Atendimento (REL-13..15): aulas registradas (Pilates) e marcações da Agenda,
// lado a lado e nunca somadas (decisão de 16/10, reconfirmada em 09/11).
export default function RelAtendimento({ dados }) {
  const [verTabela, setVerTabela] = useState(false);
  const agendaSd = dados.totalAgenda == null;

  return (
    <div className="rel-relatorio">
      <p className="rel-nota">
        Marcação na Agenda não garante que o aluno veio: as duas fontes aparecem separadas e não são somadas. A Agenda guarda{" "}
        {dados.agendaRetencaoMeses} meses; antes disso aparece <strong>s/d</strong> (sem dados).
      </p>
      <div className="rel-kpis">
        <Kpi rotulo="Aulas registradas" valor={inteiro(dados.totalAulas)} tom="destaque" detalhe="aba Pilates" />
        <Kpi
          rotulo="Marcações na Agenda"
          valor={agendaSd ? "s/d" : inteiro(dados.totalAgenda)}
          detalhe={agendaSd ? "parte do período já saiu da Agenda" : "agendamentos do período"}
        />
      </div>

      <section className="rel-bloco">
        <div className="rel-bloco-topo">
          <h3>Aulas e marcações por mês</h3>
          <button className="btn ghost rel-mini no-print" onClick={() => setVerTabela((v) => !v)}>
            {verTabela ? "Ocultar tabela" : "Ver tabela"}
          </button>
        </div>
        <BarrasMensais
          dados={dados.evolucao}
          series={SERIES}
          formato={inteiro}
          formatoEixo={inteiro}
          rotulo="Aulas registradas e marcações na Agenda por mês"
        />
        {periodoParcial(dados.de, dados.ate) && <p className="rel-nota">{NOTA_MESES_INTEIROS}</p>}
        <table className={verTabela ? "rel-tabela" : "rel-tabela so-impressao"}>
          <thead>
            <tr>
              <th>Mês</th>
              <th className="num">Aulas registradas</th>
              <th className="num">Marcações na Agenda</th>
            </tr>
          </thead>
          <tbody>
            {dados.evolucao.map((m) => (
              <tr key={m.mes}>
                <td>{mesLongo(m.mes)}</td>
                <td className="num">{inteiro(m.aulas)}</td>
                <td className="num">{n(m.agenda)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="rel-bloco">
        <h3>Por profissional</h3>
        <TabelaFontes linhas={dados.porProfissional} rotulo="Profissional" vazio="Nenhuma aula ou marcação no período." />
      </section>

      <section className="rel-bloco">
        <h3>Por aluno</h3>
        <TabelaFontes linhas={dados.porAluno} rotulo="Aluno" vazio="Nenhuma aula ou marcação no período." />
      </section>

      <div className="rel-colunas">
        <section className="rel-bloco">
          <h3>Aparelhos mais usados</h3>
          <Ranking
            itens={dados.aparelhos.map((a) => ({ nome: a.nome, valor: a.aulas }))}
            formato={(v) => plural(v, "aula", "aulas")}
            vazio="Nenhuma aula registrada no período."
          />
        </section>
        <section className="rel-bloco">
          <h3>Tipos de treino mais usados</h3>
          <Ranking
            itens={dados.treinos.map((t) => ({ nome: t.nome, valor: t.aulas }))}
            formato={(v) => plural(v, "aula", "aulas")}
            vazio="Nenhuma aula registrada no período."
          />
        </section>
      </div>
    </div>
  );
}
