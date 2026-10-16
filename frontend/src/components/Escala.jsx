import { useEffect, useMemo, useRef, useState } from "react";
import { escalaApi, financeiroApi, pacientesApi } from "../api";
import { centavosParaBR, mesAtual } from "../utils/format";

// Dias na ordem da semana (1 = segunda … 7 = domingo, padrão ISO — o mesmo número
// que vai no back). O rótulo curto é o que cabe na coluna do celular.
const DIAS = [
  { n: 1, nome: "Segunda", curto: "Seg" },
  { n: 2, nome: "Terça", curto: "Ter" },
  { n: 3, nome: "Quarta", curto: "Qua" },
  { n: 4, nome: "Quinta", curto: "Qui" },
  { n: 5, nome: "Sexta", curto: "Sex" },
  { n: 6, nome: "Sábado", curto: "Sáb" },
  { n: 7, nome: "Domingo", curto: "Dom" },
];

// Horários da grade — lista fixa no front (mesma escolha dos tipos de treino, AD-011).
// O back aceita qualquer HH:MM válido; por isso as linhas são esta lista UNIDA aos
// horários que já têm aluno (mudar a lista aqui nunca esconde uma matrícula).
const HORARIOS = [
  "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00",
  "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00",
];

const chave = (dia, hora) => `${dia}|${hora}`;

// Dia da semana de hoje no padrão ISO (1 = segunda … 7 = domingo).
const hojeISO = () => ((new Date().getDay() + 6) % 7) + 1;

const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;

// Distância mínima (px) do arraste lateral para trocar de dia na versão celular.
const SWIPE_MIN = 60;

export default function Escala({ clinic }) {
  const [matriculas, setMatriculas] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  // Quem está devendo a mensalidade do mês corrente (F2). Só admin enxerga: para
  // membro a API devolve 403, então nem pedimos — a grade funciona igual sem isso.
  const [devendo, setDevendo] = useState({});
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [celula, setCelula] = useState(null); // {dia, hora} — célula do modal aberto
  const [escolhido, setEscolhido] = useState("");
  const [salvando, setSalvando] = useState(false);
  // Celular: em vez da grade 7 colunas, um dia por vez (abre no dia de hoje).
  const [diaCel, setDiaCel] = useState(hojeISO);
  const toqueX = useRef(null);

  async function carregar() {
    setErro("");
    setCarregando(true);
    try {
      const [grade, alunos] = await Promise.all([
        escalaApi.list(clinic.id),
        pacientesApi.list(clinic.id),
      ]);
      setMatriculas(grade);
      setPacientes(alunos);

      // Falha aqui NÃO pode derrubar a escala: o marcador é um extra, a grade é o
      // que a recepção veio ver. Por isso vai num catch próprio e silencioso.
      if (clinic.role === "admin") {
        try {
          const m = await financeiroApi.mensalidades(clinic.id, mesAtual());
          const mapa = {};
          for (const a of m.alunos) {
            if (a.emAbertoCentavos > 0) mapa[a.pacienteId] = a.emAbertoCentavos;
          }
          setDevendo(mapa);
        } catch {
          setDevendo({});
        }
      }
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, [clinic.id]);

  // Alunos de cada célula, indexados por "dia|hora" (a grade vem ordenada do back).
  const porCelula = useMemo(() => {
    const mapa = new Map();
    for (const m of matriculas) {
      const k = chave(m.dia, m.hora);
      if (!mapa.has(k)) mapa.set(k, []);
      mapa.get(k).push(m);
    }
    return mapa;
  }, [matriculas]);

  // Linhas = horários fixos + qualquer horário que já tenha aluno (nada fica invisível).
  const linhas = useMemo(() => {
    const horas = new Set(HORARIOS);
    for (const m of matriculas) horas.add(m.hora);
    return [...horas].sort();
  }, [matriculas]);

  const totalPorDia = useMemo(() => {
    const conta = {};
    for (const m of matriculas) conta[m.dia] = (conta[m.dia] || 0) + 1;
    return conta;
  }, [matriculas]);

  // Pessoas distintas por dia (quem faz 2 horários no mesmo dia conta 1 vez).
  const alunosPorDia = useMemo(() => {
    const sets = {};
    for (const m of matriculas) (sets[m.dia] ||= new Set()).add(m.pacienteId);
    return Object.fromEntries(Object.entries(sets).map(([d, s]) => [d, s.size]));
  }, [matriculas]);

  const alunosOrdenados = useMemo(
    () => [...pacientes].sort((a, b) => (a.nome || "").localeCompare(b.nome || "", "pt-BR")),
    [pacientes]
  );

  // No combo, só quem ainda não está naquele horário.
  const disponiveis = useMemo(() => {
    if (!celula) return [];
    const jaEstao = new Set(
      (porCelula.get(chave(celula.dia, celula.hora)) || []).map((m) => m.pacienteId)
    );
    return alunosOrdenados.filter((p) => !jaEstao.has(p.id));
  }, [celula, porCelula, alunosOrdenados]);

  function abrirCelula(dia, hora) {
    setErro("");
    setEscolhido("");
    setCelula({ dia, hora });
  }

  function fechar() {
    setCelula(null);
    setEscolhido("");
  }

  async function adicionar() {
    if (!escolhido) return;
    setSalvando(true);
    setErro("");
    try {
      const nova = await escalaApi.matricular(clinic.id, {
        dia: celula.dia,
        hora: celula.hora,
        pacienteId: escolhido,
      });
      setMatriculas((atual) => [...atual, nova]);
      fechar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  async function remover(m) {
    const dia = DIAS.find((d) => d.n === m.dia)?.nome || "";
    if (!confirm(`Tirar ${m.nome} de ${dia}, ${m.hora}?`)) return;
    setErro("");
    try {
      await escalaApi.remover(clinic.id, m.dia, m.hora, m.pacienteId);
      setMatriculas((atual) =>
        atual.filter(
          (x) => !(x.dia === m.dia && x.hora === m.hora && x.pacienteId === m.pacienteId)
        )
      );
    } catch (e) {
      setErro(e.message);
      carregar(); // ressincroniza se o back e a tela divergiram
    }
  }

  // Arraste lateral na lista do celular: esquerda = próximo dia, direita = anterior.
  function fimToque(e) {
    if (toqueX.current == null) return;
    const dx = e.changedTouches[0].clientX - toqueX.current;
    toqueX.current = null;
    if (Math.abs(dx) < SWIPE_MIN) return;
    setDiaCel((d) => (dx < 0 ? (d % 7) + 1 : ((d + 5) % 7) + 1));
  }

  // Chip do aluno — o mesmo na grade (desktop) e na lista do dia (celular).
  function chipAluno(m) {
    return (
      <span
        key={m.pacienteId}
        className={devendo[m.pacienteId] ? "aluno-chip devendo" : "aluno-chip"}
      >
        {devendo[m.pacienteId] ? (
          <span
            className="ponto-devendo"
            title={`Mensalidade em aberto: R$ ${centavosParaBR(devendo[m.pacienteId])}`}
          >
            ●
          </span>
        ) : null}
        <span className="aluno-nome" title={m.nome}>
          {m.nome}
        </span>
        <button
          type="button"
          className="aluno-x"
          title={`Tirar ${m.nome} deste horário`}
          onClick={() => remover(m)}
        >
          ✕
        </button>
      </span>
    );
  }

  const semAlunos = pacientes.length === 0;
  const diaCelInfo = DIAS.find((d) => d.n === diaCel);
  const hoje = hojeISO();

  return (
    <div>
      {erro && <div className="erro">{erro}</div>}

      <div className="card">
        <h2>Escala da semana ({carregando ? "…" : matriculas.length} matrículas)</h2>

        {carregando ? (
          <div className="loading">
            <span className="spinner" />
            Carregando a escala…
          </div>
        ) : semAlunos ? (
          <p className="muted">
            Nenhum aluno cadastrado ainda. Cadastre um paciente na aba Pacientes para montar a
            escala.
          </p>
        ) : (
          <>
            <p className="muted escala-dica">
              Clique em <strong>+</strong> num horário para colocar um aluno; no <strong>✕</strong>{" "}
              ao lado do nome para tirá-lo.
            </p>
            <div className="escala-wrap">
              <table className="escala">
                <thead>
                  <tr>
                    <th className="col-hora">Horário</th>
                    {DIAS.map((d) => (
                      <th key={d.n}>
                        <span className="dia-nome">{d.nome}</span>
                        <span className="dia-curto">{d.curto}</span>
                        <span className="dia-conta">{totalPorDia[d.n] || 0}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {linhas.map((hora) => (
                    <tr key={hora}>
                      <th className="col-hora">{hora}</th>
                      {DIAS.map((d) => {
                        const alunos = porCelula.get(chave(d.n, hora)) || [];
                        return (
                          <td key={d.n} className={alunos.length ? "cel cheia" : "cel"}>
                            {alunos.map(chipAluno)}
                            <button
                              type="button"
                              className="cel-add"
                              title={`Adicionar aluno — ${d.nome}, ${hora}`}
                              onClick={() => abrirCelula(d.n, hora)}
                            >
                              +
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Versão celular (só aparece ≤ 640px, ver App.css): um dia por vez. */}
            <div className="escala-cel">
              <div className="escala-dias" role="tablist">
                {DIAS.map((d) => (
                  <button
                    key={d.n}
                    type="button"
                    role="tab"
                    aria-selected={d.n === diaCel}
                    className={
                      "escala-dia" + (d.n === diaCel ? " on" : "") + (d.n === hoje ? " hoje" : "")
                    }
                    onClick={() => setDiaCel(d.n)}
                  >
                    <span className="escala-dia-curto">{d.curto}</span>
                    <span className="escala-dia-conta">{totalPorDia[d.n] || 0}</span>
                  </button>
                ))}
              </div>

              <div className="escala-dia-titulo">
                <strong>{diaCelInfo?.nome}</strong>
                {diaCel === hoje && <span className="escala-hoje">hoje</span>}
                <span className="muted">
                  {plural(alunosPorDia[diaCel] || 0, "aluno", "alunos")} ·{" "}
                  {plural(totalPorDia[diaCel] || 0, "aula", "aulas")}
                </span>
              </div>

              <div
                key={diaCel}
                className="escala-horarios"
                onTouchStart={(e) => (toqueX.current = e.touches[0].clientX)}
                onTouchEnd={fimToque}
              >
                {linhas.map((hora) => {
                  const alunos = porCelula.get(chave(diaCel, hora)) || [];
                  return (
                    <div key={hora} className={alunos.length ? "escala-slot cheio" : "escala-slot"}>
                      <div className="escala-slot-hora">{hora}</div>
                      <div className="escala-slot-alunos">
                        {alunos.length ? alunos.map(chipAluno) : <span className="muted">Livre</span>}
                      </div>
                      <button
                        type="button"
                        className="escala-slot-add"
                        aria-label={`Adicionar aluno — ${diaCelInfo?.nome}, ${hora}`}
                        onClick={() => abrirCelula(diaCel, hora)}
                      >
                        +
                      </button>
                    </div>
                  );
                })}
              </div>
              <p className="muted escala-dica-cel">Arraste para o lado para trocar de dia.</p>
            </div>
          </>
        )}
      </div>

      {celula && (
        <div className="modal-overlay" onClick={fechar}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>
              {DIAS.find((d) => d.n === celula.dia)?.nome}, {celula.hora}
            </h2>
            {disponiveis.length === 0 ? (
              <p className="muted">Todos os alunos cadastrados já estão neste horário.</p>
            ) : (
              <>
                <label className="escala-label">Aluno</label>
                <select
                  className="escala-select"
                  value={escolhido}
                  onChange={(e) => setEscolhido(e.target.value)}
                >
                  <option value="">— escolha um aluno —</option>
                  {disponiveis.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nome}
                    </option>
                  ))}
                </select>
              </>
            )}
            <div className="modal-actions">
              <button type="button" className="btn" onClick={fechar}>
                Fechar
              </button>
              {disponiveis.length > 0 && (
                <button
                  type="button"
                  className="btn primary"
                  disabled={!escolhido || salvando}
                  onClick={adicionar}
                >
                  {salvando ? "Adicionando…" : "Adicionar"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
