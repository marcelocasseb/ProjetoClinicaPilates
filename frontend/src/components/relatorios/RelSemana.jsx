import { DIAS } from "../Escala";
import { Kpi } from "./graficos";
import { dataBR, diaMes, inteiro } from "./formato";

// Data (AAAA-MM-DD) do dia n (1 = segunda) da semana que começa em `inicio`.
function dataDoDia(inicio, n) {
  const [a, m, d] = inicio.split("-").map(Number);
  const dt = new Date(Date.UTC(a, m - 1, d + n - 1));
  return dt.toISOString().slice(0, 10);
}

// Marcas legíveis em P&B: ● aula registrada, ○ marcação na Agenda.
const marcas = ({ aula, agenda }) => "●".repeat(aula) + "○".repeat(agenda);

// Quem passou na semana (REL-22): aluno × dia, marcando a fonte.
export default function RelSemana({ dados }) {
  return (
    <div className="rel-relatorio">
      {dados.agendaDesde && (
        <p className="rel-nota aviso">
          A Agenda guarda 4 meses: as marcações desta semana contam a partir de {dataBR(dados.agendaDesde)}.
        </p>
      )}
      {!dados.agendaDisponivel && (
        <p className="rel-nota aviso">
          As marcações da Agenda desta semana já expiraram (a Agenda guarda 4 meses). Só as aulas registradas aparecem.
        </p>
      )}
      <div className="rel-kpis">
        <Kpi rotulo="Alunos na semana" valor={inteiro(dados.distintos)} tom="destaque" />
        <Kpi rotulo="Aulas registradas" valor={inteiro(dados.totalAulas)} />
        <Kpi
          rotulo="Marcações na Agenda"
          valor={dados.agendaDisponivel ? inteiro(dados.totalAgenda) : "s/d"}
        />
      </div>

      <section className="rel-bloco">
        <div className="rel-bloco-topo">
          <h3>Frequência da semana</h3>
          <span className="rel-legenda-texto">● aula registrada · ○ marcação na Agenda</span>
        </div>
        {dados.alunos.length === 0 ? (
          <p className="muted rel-vazio">Ninguém teve aula registrada ou marcação nesta semana.</p>
        ) : (
          <div className="rel-grafico-rolagem">
            <table className="rel-tabela rel-semana">
              <thead>
                <tr>
                  <th>Aluno</th>
                  {DIAS.map((d) => (
                    <th key={d.n} className="centro">
                      {d.curto}
                      <span className="rel-th-data">{diaMes(dataDoDia(dados.inicio, d.n))}</span>
                    </th>
                  ))}
                  <th className="num">Total</th>
                </tr>
              </thead>
              <tbody>
                {dados.alunos.map((a, i) => (
                  <tr key={i}>
                    <td>
                      {a.nome}
                      {a.novo ? <span className="rel-tag">novo</span> : null}
                    </td>
                    {DIAS.map((d) => {
                      const dia = a.dias[String(d.n)];
                      return (
                        <td
                          key={d.n}
                          className="centro rel-marcas"
                          title={`${d.nome}: ${dia.aula} aula(s) registrada(s), ${dia.agenda} marcação(ões) na Agenda`}
                        >
                          {marcas(dia)}
                        </td>
                      );
                    })}
                    <td className="num">{a.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
