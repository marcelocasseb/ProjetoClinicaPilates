import { useEffect, useMemo, useRef, useState } from "react";
import { escalaApi, financeiroApi } from "../api";
import { getClaims } from "../auth";
import { centavosParaBR, mesAtual } from "../utils/format";

// Tela inicial: saudação + o resumo do dia. Tudo sai de APIs que já existem —
// a grade semanal (/escala) diz quem vem hoje, e as mensalidades do mês (só
// admin) dizem quem vence hoje. Nenhum endpoint novo.

const DIAS_SEMANA = [
  "Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira",
  "Quinta-feira", "Sexta-feira", "Sábado",
];
const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

// Duração assumida de uma aula para marcar "agora" / "concluída" na agenda.
const DURACAO_AULA_MIN = 60;

// Período do dia: define a saudação, o ícone e o tom do hero.
function periodoDe(hora) {
  if (hora >= 5 && hora < 12) return { id: "manha", saudacao: "Bom dia" };
  if (hora >= 12 && hora < 18) return { id: "tarde", saudacao: "Boa tarde" };
  return { id: "noite", saudacao: "Boa noite" };
}

// getDay() é 0=domingo; a escala usa ISO (1=segunda … 7=domingo).
const diaIso = (d) => (d.getDay() === 0 ? 7 : d.getDay());

const minutos = (hhmm) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

// Dia em que a mensalidade vence NESTE mês. "Dia 31" num mês de 30 dias vence no
// último dia — senão o aluno nunca apareceria como "vence hoje" em fevereiro.
function diaVencimentoNoMes(diaVencimento, agora) {
  if (!diaVencimento) return null;
  const ultimo = new Date(agora.getFullYear(), agora.getMonth() + 1, 0).getDate();
  return Math.min(diaVencimento, ultimo);
}

// Primeiro nome para a saudação. As contas nascem sem o atributo `name` no
// Cognito, então o fallback é o e-mail: "marcelo.casseb@…" -> "Marcelo".
function primeiroNome() {
  const c = getClaims() || {};
  const nome = (c.name || "").trim().split(/\s+/)[0];
  const base = nome || (c.email || "").split("@")[0].split(/[._\-+\d]+/)[0];
  return base ? base.charAt(0).toUpperCase() + base.slice(1).toLowerCase() : "";
}

const prefereMenosMovimento = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Número que "sobe" de 0 até o valor, com desaceleração no final.
function useContador(alvo, ativo) {
  const [valor, setValor] = useState(0);
  useEffect(() => {
    if (!ativo) return;
    if (prefereMenosMovimento() || alvo === 0) {
      setValor(alvo);
      return;
    }
    const inicio = performance.now();
    const dur = 1100;
    let raf;
    const passo = (t) => {
      const p = Math.min(1, (t - inicio) / dur);
      setValor(Math.round(alvo * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(passo);
    };
    raf = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(raf);
  }, [alvo, ativo]);
  return valor;
}

// Relógio que re-renderiza a cada virada de minuto (troca a saudação sozinho).
function useAgora() {
  const [agora, setAgora] = useState(() => new Date());
  useEffect(() => {
    let timer;
    const agendar = () => {
      const d = new Date();
      timer = setTimeout(() => {
        setAgora(new Date());
        agendar();
      }, 60_000 - (d.getSeconds() * 1000 + d.getMilliseconds()) + 50);
    };
    agendar();
    return () => clearTimeout(timer);
  }, []);
  return agora;
}

// ---------------------------------------------------------------------------
// Ícones (SVG inline, traço fino, herdam a cor)

function IconePeriodo({ periodo }) {
  if (periodo === "noite") {
    return (
      <svg viewBox="0 0 64 64" className="ini-astro" aria-hidden="true">
        <path d="M42 10a22 22 0 1 0 12 30A18 18 0 0 1 42 10z" fill="currentColor" />
        <circle cx="16" cy="14" r="1.4" fill="currentColor" className="ini-estrela" />
        <circle cx="54" cy="52" r="1.1" fill="currentColor" className="ini-estrela e2" />
        <circle cx="8" cy="40" r="1" fill="currentColor" className="ini-estrela e3" />
      </svg>
    );
  }
  const raios = Array.from({ length: 12 }, (_, i) => i * 30);
  return (
    <svg viewBox="0 0 64 64" className="ini-astro" aria-hidden="true">
      <g className="ini-raios">
        {raios.map((a) => (
          <line
            key={a}
            x1="32" y1="6" x2="32" y2="12"
            stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
            transform={`rotate(${a} 32 32)`}
          />
        ))}
      </g>
      <circle cx="32" cy="32" r={periodo === "tarde" ? 13 : 12} fill="currentColor" />
    </svg>
  );
}

const Icone = {
  aulas: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="5" width="17" height="15" rx="3" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
      <circle cx="12" cy="15" r="1.6" />
    </svg>
  ),
  alunos: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="9" cy="8.5" r="3.2" />
      <path d="M3 19.5c.6-3.2 3-5 6-5s5.4 1.8 6 5" />
      <circle cx="17" cy="9.5" r="2.4" />
      <path d="M16 14.6c2.6.1 4.3 1.7 4.9 4.4" />
    </svg>
  ),
  vencimento: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="6" width="18" height="13" rx="2.5" />
      <path d="M3 10.5h18M7 15h4" />
    </svg>
  ),
  atraso: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3.5 21.5 20h-19z" />
      <path d="M12 10v4.5M12 17.2v.1" />
    </svg>
  ),
  proxima: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  ),
  seta: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h13M13 6l6 6-6 6" />
    </svg>
  ),
};

// ---------------------------------------------------------------------------

function CardKpi({ icone, valor, rotulo, detalhe, tom, carregando, onClick, indice, texto }) {
  const n = useContador(typeof valor === "number" ? valor : 0, !carregando);
  return (
    <button
      type="button"
      className={`ini-kpi ${tom || ""}`}
      style={{ "--i": indice }}
      onClick={onClick}
      disabled={!onClick}
    >
      <span className="ini-kpi-icone">{icone}</span>
      <span className="ini-kpi-num">
        {carregando ? <span className="ini-skel" /> : texto ?? n}
      </span>
      <span className="ini-kpi-rotulo">{rotulo}</span>
      {detalhe && <span className="ini-kpi-detalhe">{detalhe}</span>}
      {onClick && <span className="ini-kpi-seta">{Icone.seta}</span>}
    </button>
  );
}

function ListaPendencias({ titulo, alunos, detalhe, tom }) {
  return (
    <div className={`ini-pend ${tom || ""}`}>
      <h3>
        {titulo} <span>{alunos.length}</span>
      </h3>
      <ul>
        {alunos.map((a) => {
          const obs = [detalhe?.(a), a.status === "parcial" && "pagou parte"].filter(Boolean);
          return (
            <li key={a.pacienteId}>
              <span className="ini-avatar grande">{(a.nome || "?").charAt(0).toUpperCase()}</span>
              <span className="ini-venc-nome">
                {a.nome}
                {obs.length > 0 && <small>{obs.join(" · ")}</small>}
              </span>
              <span className="ini-venc-valor">R$ {centavosParaBR(a.emAbertoCentavos)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function Inicio({ clinic, onNavegar }) {
  const isAdmin = clinic.role === "admin";
  const agora = useAgora();
  const nome = useMemo(primeiroNome, []);

  const [grade, setGrade] = useState([]);
  const [mensal, setMensal] = useState(null); // null = não carregado / sem acesso
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const montado = useRef(true);

  useEffect(() => {
    montado.current = true;
    (async () => {
      try {
        const g = await escalaApi.list(clinic.id);
        if (montado.current) setGrade(g);
      } catch (e) {
        if (montado.current) setErro(e.message || "Não foi possível carregar a agenda.");
      }
      // Mensalidades são um extra de admin: falha aqui não derruba a tela.
      if (isAdmin) {
        try {
          const m = await financeiroApi.mensalidades(clinic.id, mesAtual());
          if (montado.current) setMensal(m);
        } catch {
          /* ignora — o card mostra "—" */
        }
      }
      if (montado.current) setCarregando(false);
    })();
    return () => {
      montado.current = false;
    };
  }, [clinic.id, isAdmin]);

  const periodo = periodoDe(agora.getHours());
  const hojeIso = diaIso(agora);
  const minAgora = agora.getHours() * 60 + agora.getMinutes();

  // Mensalidades do mês com saldo em aberto (isentos e já pagos ficam de fora),
  // separadas em "vence hoje" e "atrasada" (vencimento deste mês já passou).
  // Só o mês corrente: o plano não tem data de início, então olhar meses
  // anteriores acusaria atraso de quem nem era aluno na época.
  const { vencendo, atrasados } = useMemo(() => {
    const hoje = agora.getDate();
    const vencendo = [];
    const atrasados = [];
    for (const a of mensal?.alunos || []) {
      if (!a.temPlano || a.emAbertoCentavos <= 0) continue;
      const dia = diaVencimentoNoMes(a.diaVencimento, agora);
      if (dia === hoje) vencendo.push(a);
      else if (dia && dia < hoje) atrasados.push({ ...a, diasAtraso: hoje - dia });
    }
    atrasados.sort((x, y) => y.diasAtraso - x.diasAtraso);
    return { vencendo, atrasados };
    // agora.getDate() basta como dependência: só muda na virada do dia.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mensal, agora.getDate()]);
  const situacaoAluno = useMemo(() => {
    const m = new Map();
    for (const a of vencendo) m.set(a.pacienteId, "vence");
    for (const a of atrasados) m.set(a.pacienteId, "atrasada");
    return m;
  }, [vencendo, atrasados]);
  const temPendencia = isAdmin && (vencendo.length > 0 || atrasados.length > 0);
  const somaAberto = (lista) =>
    `R$ ${centavosParaBR(lista.reduce((s, a) => s + a.emAbertoCentavos, 0))} em aberto`;

  // Agenda de hoje agrupada por horário, com o estado de cada aula.
  const agenda = useMemo(() => {
    const porHora = new Map();
    for (const m of grade) {
      if (m.dia !== hojeIso) continue;
      if (!porHora.has(m.hora)) porHora.set(m.hora, []);
      porHora.get(m.hora).push(m);
    }
    const horas = [...porHora.keys()].sort();
    let proximaMarcada = false;
    return horas.map((hora) => {
      const ini = minutos(hora);
      let estado = "futura";
      if (minAgora >= ini + DURACAO_AULA_MIN) estado = "concluida";
      else if (minAgora >= ini) estado = "agora";
      else if (!proximaMarcada) {
        estado = "proxima";
        proximaMarcada = true;
      }
      return { hora, alunos: porHora.get(hora), estado };
    });
  }, [grade, hojeIso, minAgora]);

  const totalAulas = agenda.length;
  const alunosHoje = new Set(agenda.flatMap((a) => a.alunos.map((x) => x.pacienteId))).size;
  const emAndamento = agenda.find((a) => a.estado === "agora");
  const proxima = agenda.find((a) => a.estado === "proxima");
  const restantes = agenda.filter((a) => a.estado !== "concluida").length;

  const dataExtenso = `${DIAS_SEMANA[agora.getDay()]}, ${agora.getDate()} de ${MESES[agora.getMonth()]}`;
  const relogio = agora.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  let resumo;
  if (carregando) resumo = "Preparando o seu dia…";
  else if (erro) resumo = "Não conseguimos carregar a agenda agora.";
  else if (totalAulas === 0) resumo = "Nenhuma aula na grade hoje. Um bom dia para descansar.";
  else if (restantes === 0) resumo = "Todas as aulas de hoje já aconteceram. Missão cumprida.";
  else if (emAndamento)
    resumo = `Aula das ${emAndamento.hora} em andamento, com ${emAndamento.alunos.length} ${emAndamento.alunos.length === 1 ? "aluno" : "alunos"} no estúdio.`;
  else resumo = `Ainda ${restantes === 1 ? "falta 1 aula" : `faltam ${restantes} aulas`} hoje. A próxima começa às ${proxima.hora}.`;

  return (
    <div className="inicio">
      <section className={`ini-hero ${periodo.id}`}>
        <div className="ini-aneis" aria-hidden="true">
          <span /><span /><span /><span />
        </div>
        <div className="ini-brilho" aria-hidden="true" />

        <div className="ini-hero-texto">
          <p className="ini-data">{dataExtenso}</p>
          <h1 className="ini-saudacao">
            <span className="ini-saudacao-linha">{periodo.saudacao}{nome ? "," : "."}</span>
            {nome && <span className="ini-nome">{nome}.</span>}
          </h1>
          <p className="ini-resumo">{resumo}</p>
        </div>

        <div className="ini-hero-lado">
          <IconePeriodo periodo={periodo.id} />
          <time className="ini-relogio" dateTime={agora.toISOString()}>{relogio}</time>
        </div>
      </section>

      {erro && <p className="error ini-erro">{erro}</p>}

      <section className={`ini-kpis ${isAdmin ? "cinco" : ""}`}>
        <CardKpi
          indice={0}
          icone={Icone.aulas}
          valor={totalAulas}
          rotulo={totalAulas === 1 ? "aula agendada hoje" : "aulas agendadas hoje"}
          detalhe={
            totalAulas > 0 && !carregando
              ? `${agenda[0].hora} às ${agenda[agenda.length - 1].hora}`
              : null
          }
          carregando={carregando}
          onClick={() => onNavegar("escala")}
        />
        <CardKpi
          indice={1}
          icone={Icone.alunos}
          valor={alunosHoje}
          rotulo={alunosHoje === 1 ? "aluno deve estar presente" : "alunos devem estar presentes"}
          carregando={carregando}
          onClick={() => onNavegar("pacientes")}
        />
        {isAdmin && (
          <CardKpi
            indice={2}
            tom={vencendo.length > 0 ? "aviso" : ""}
            icone={Icone.vencimento}
            valor={vencendo.length}
            texto={!carregando && !mensal ? "—" : undefined}
            rotulo={vencendo.length === 1 ? "mensalidade vence hoje" : "mensalidades vencem hoje"}
            detalhe={vencendo.length > 0 ? somaAberto(vencendo) : null}
            carregando={carregando}
            onClick={() => onNavegar("financeiro")}
          />
        )}
        {isAdmin && (
          <CardKpi
            indice={3}
            tom={atrasados.length > 0 ? "alerta" : ""}
            icone={Icone.atraso}
            valor={atrasados.length}
            texto={!carregando && !mensal ? "—" : undefined}
            rotulo={
              atrasados.length === 1
                ? "aluno com mensalidade atrasada"
                : "alunos com mensalidade atrasada"
            }
            detalhe={atrasados.length > 0 ? somaAberto(atrasados) : null}
            carregando={carregando}
            onClick={() => onNavegar("financeiro")}
          />
        )}
        <CardKpi
          indice={isAdmin ? 4 : 2}
          tom="destaque"
          icone={Icone.proxima}
          texto={emAndamento ? "Agora" : proxima ? proxima.hora : "—"}
          rotulo={
            emAndamento
              ? `aula das ${emAndamento.hora} em andamento`
              : proxima
                ? "próxima aula"
                : "sem mais aulas hoje"
          }
          detalhe={
            (emAndamento || proxima)
              ? `${(emAndamento || proxima).alunos.length} ${(emAndamento || proxima).alunos.length === 1 ? "aluno" : "alunos"}`
              : null
          }
          carregando={carregando}
        />
      </section>

      <div className={`ini-paineis ${temPendencia ? "com-lado" : ""}`}>
        <section className="card ini-agenda">
          <h2>Agenda de hoje</h2>
          {carregando ? (
            <div className="ini-agenda-skel">
              <span className="ini-skel" /><span className="ini-skel" /><span className="ini-skel" />
            </div>
          ) : agenda.length === 0 ? (
            <div className="ini-vazio">
              <svg viewBox="0 0 64 64" aria-hidden="true">
                <circle cx="32" cy="32" r="22" />
                <circle cx="32" cy="32" r="14" />
                <circle cx="32" cy="32" r="6" />
              </svg>
              <p>Nenhum aluno na grade de {DIAS_SEMANA[agora.getDay()].toLowerCase()}.</p>
              <button className="btn ghost" onClick={() => onNavegar("escala")}>
                Abrir a escala
              </button>
            </div>
          ) : (
            <ol className="ini-timeline">
              {agenda.map((a, i) => (
                <li key={a.hora} className={`ini-aula ${a.estado}`} style={{ "--i": i }}>
                  <span className="ini-aula-hora">{a.hora}</span>
                  <span className="ini-aula-marco" aria-hidden="true" />
                  <div className="ini-aula-corpo">
                    <div className="ini-aula-topo">
                      <strong>
                        {a.alunos.length} {a.alunos.length === 1 ? "aluno" : "alunos"}
                      </strong>
                      {a.estado === "agora" && <span className="ini-selo agora">Agora</span>}
                      {a.estado === "proxima" && <span className="ini-selo proxima">Próxima</span>}
                      {a.estado === "concluida" && <span className="ini-selo feita">Concluída</span>}
                    </div>
                    <div className="ini-chips">
                      {a.alunos.map((al) => (
                        <span
                          key={al.pacienteId}
                          className={`ini-chip ${situacaoAluno.get(al.pacienteId) || ""}`}
                          title={
                            situacaoAluno.get(al.pacienteId) === "atrasada"
                              ? "Mensalidade atrasada"
                              : situacaoAluno.get(al.pacienteId) === "vence"
                                ? "Mensalidade vence hoje"
                                : undefined
                          }
                        >
                          <span className="ini-avatar">{(al.nome || "?").charAt(0).toUpperCase()}</span>
                          {al.nome}
                        </span>
                      ))}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        {temPendencia && (
          <section className="card ini-vencimentos">
            <h2>Mensalidades</h2>
            {atrasados.length > 0 && (
              <ListaPendencias
                titulo="Atrasadas"
                alunos={atrasados}
                detalhe={(a) => `${a.diasAtraso} ${a.diasAtraso === 1 ? "dia" : "dias"} de atraso`}
              />
            )}
            {vencendo.length > 0 && (
              <ListaPendencias titulo="Vencem hoje" alunos={vencendo} tom="vence" />
            )}
            <button className="btn primary ini-venc-btn" onClick={() => onNavegar("financeiro")}>
              Ir para as mensalidades
            </button>
          </section>
        )}
      </div>
    </div>
  );
}
