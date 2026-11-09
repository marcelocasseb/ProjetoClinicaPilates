import { DIAS, HORARIOS } from "../Escala";
import { Kpi, MapaCalor, Ranking } from "./graficos";
import { inteiro, plural } from "./formato";

const nomeDia = (n) => DIAS.find((d) => d.n === n)?.nome || String(n);

// Ocupação da escala (REL-11, REL-12): grade atual, sem histórico.
export default function RelOcupacao({ dados }) {
  const vazia = dados.matriculas === 0;
  return (
    <div className="rel-relatorio">
      <p className="rel-nota">
        Mostra a grade <strong>atual</strong> da Escala. A escala não guarda histórico, então este relatório não muda com o mês.
      </p>
      {vazia ? (
        <p className="muted rel-vazio">A clínica ainda não usa a Escala.</p>
      ) : (
        <>
          <div className="rel-kpis">
            <Kpi rotulo="Matrículas na grade" valor={inteiro(dados.matriculas)} tom="destaque" />
            <Kpi rotulo="Alunos na grade" valor={inteiro(dados.alunosDistintos)} />
            <Kpi
              rotulo="Média por horário ocupado"
              valor={String(dados.mediaPorHorarioOcupado).replace(".", ",")}
              detalhe="alunos"
            />
            <Kpi rotulo="Alunos fora da escala" valor={inteiro(dados.foraDaEscala.length)} />
          </div>

          <section className="rel-bloco">
            <h3>Alunos por dia e horário</h3>
            <MapaCalor celulas={dados.celulas} dias={DIAS} horarios={HORARIOS} />
          </section>

          <div className="rel-colunas">
            <section className="rel-bloco">
              <h3>Horários mais cheios</h3>
              <Ranking
                itens={dados.top5.map((c) => ({ nome: `${nomeDia(c.dia)} ${c.hora}`, valor: c.alunos }))}
                formato={(v) => plural(v, "aluno", "alunos")}
              />
            </section>
            <section className="rel-bloco">
              <h3>Alunos ativos fora da escala</h3>
              {dados.foraDaEscala.length === 0 ? (
                <p className="muted rel-vazio">Todos os alunos ativos têm horário na grade.</p>
              ) : (
                <ul className="rel-nomes">
                  {dados.foraDaEscala.map((a) => (
                    <li key={a.id}>{a.nome}</li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
