import { useEffect, useState } from "react";
import { pacientesApi, aparelhosApi, sessoesApi, profissionaisApi } from "../api";
import { onlyDigits, maskCpf, hojeISO, formatDataBR, primeiroEUltimoNome } from "../utils/format";
import { getClaims } from "../auth";

// Valor do select para a aula antiga cujo profissional é texto livre (sem id).
const LEGADO = "__legado";

// Tipos de treino — lista fixa (hardcode no front, AD-011). O back só guarda o texto.
const TIPOS_TREINO = [
  "Membros superiores",
  "Membros inferiores",
  "Abdômen",
  "Força",
  "Mobilidade",
  "Postural",
  "Alongamento",
];

// O profissional vem do MESMO cadastro da Agenda (nome padronizado = relatório por
// profissional confiável). Quem conduz a aula é, quase sempre, quem está logado: se
// o nome do token bate com alguém do cadastro, já vem selecionado (e continua
// trocável). Sem `name` no Cognito ou sem correspondência, fica em branco — chutar
// pelo e-mail escreveria coisa como "Natsousa2" num registro clínico.
const normaliza = (s) =>
  (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();

function profissionalPadrao(profissionais) {
  const nome = getClaims()?.name;
  if (!nome) return "";
  const alvos = new Set([normaliza(nome), normaliza(primeiroEUltimoNome(nome))]);
  return profissionais.find((p) => alvos.has(normaliza(p.nome)))?.id || "";
}

function vazio(profissionais = []) {
  return {
    data: hojeISO(),
    profissionalId: profissionalPadrao(profissionais),
    profissionalLegado: "", // texto livre de aula antiga (só exibição/preservação)
    observacao: "",
    aparelhos: [],
  };
}

export default function Pilates({ clinic }) {
  const [pacientes, setPacientes] = useState([]);
  const [busca, setBusca] = useState("");
  const [view, setView] = useState("lista"); // "lista" (seleção do aluno) | "aula"
  const [aluno, setAluno] = useState(null);

  const [catalogo, setCatalogo] = useState([]); // aparelhos ativos da clínica
  const [profissionais, setProfissionais] = useState([]); // cadastro (o mesmo da Agenda)
  const [lista, setLista] = useState([]); // aulas do aluno
  const [form, setForm] = useState(vazio());
  const [editId, setEditId] = useState(null);
  const [readonly, setReadonly] = useState(false);
  const [comboSel, setComboSel] = useState(""); // aparelho "atual" (a que os treinos se aplicam)
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);
  const [carregandoLista, setCarregandoLista] = useState(true);
  const [carregandoAula, setCarregandoAula] = useState(false);

  async function carregarPacientes() {
    setErro("");
    setCarregandoLista(true);
    try {
      setPacientes(await pacientesApi.list(clinic.id));
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregandoLista(false);
    }
  }

  useEffect(() => {
    carregarPacientes();
    profissionaisApi.list(clinic.id).then(setProfissionais).catch(() => {});
    setView("lista");
    setBusca("");
    setAluno(null);
  }, [clinic.id]);

  async function carregarAula(p) {
    setErro("");
    setCarregandoAula(true);
    try {
      const [cat, aulas] = await Promise.all([
        aparelhosApi.list(clinic.id),
        sessoesApi.list(clinic.id, p.id),
      ]);
      setCatalogo(cat);
      setLista(aulas);
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregandoAula(false);
    }
  }

  function selecionarAluno(p) {
    setAluno(p);
    setForm(vazio(profissionais));
    setEditId(null);
    setReadonly(false);
    setComboSel("");
    setView("aula");
    carregarAula(p);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function voltarLista() {
    setView("lista");
    setAluno(null);
    setForm(vazio(profissionais));
    setEditId(null);
    setReadonly(false);
    setErro("");
    carregarPacientes();
  }

  // ---- edição do form da aula ----
  function setCampo(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  // Clica num treino do aparelho ATUAL (comboSel): adiciona ou remove o par
  // (aparelho + treino) da aula. Mesmo aparelho pode ter vários treinos.
  function toggleTreinoAtual(treino) {
    if (!comboSel) return;
    const ap = catalogo.find((a) => a.id === comboSel);
    if (!ap) return;
    setForm((f) => {
      const existe = f.aparelhos.find((a) => a.aparelhoId === ap.id);
      if (!existe) {
        return { ...f, aparelhos: [...f.aparelhos, { aparelhoId: ap.id, nome: ap.nome, treinos: [treino] }] };
      }
      const tem = existe.treinos.includes(treino);
      const aparelhos = f.aparelhos
        .map((a) => {
          if (a.aparelhoId !== ap.id) return a;
          const treinos = tem ? a.treinos.filter((t) => t !== treino) : [...a.treinos, treino];
          return { ...a, treinos };
        })
        // remove o aparelho atual se ficou sem nenhum treino
        .filter((a) => a.aparelhoId !== ap.id || a.treinos.length > 0);
      return { ...f, aparelhos };
    });
  }

  // Remove um par (linha da lista). `treino` null = aparelho sem treino (legado).
  function removerPar(aparelhoId, treino) {
    setForm((f) => {
      const aparelhos = f.aparelhos
        .map((a) =>
          a.aparelhoId === aparelhoId
            ? { ...a, treinos: treino == null ? [] : a.treinos.filter((t) => t !== treino) }
            : a
        )
        .filter((a) => !(a.aparelhoId === aparelhoId && a.treinos.length === 0));
      return { ...f, aparelhos };
    });
  }

  function montarPayload() {
    const txt = (v) => (v && v.trim() ? v.trim() : null);
    // Do cadastro: manda só o id (o backend grava o nome). Aula antiga mantida como
    // estava: reenvia o texto livre dela, sem id.
    const legado = form.profissionalId === LEGADO;
    return {
      data: form.data || null,
      profissionalId: legado ? null : form.profissionalId || null,
      profissional: legado ? txt(form.profissionalLegado) : null,
      observacao: txt(form.observacao),
      aparelhos: form.aparelhos.map((a) => ({
        aparelhoId: a.aparelhoId || null,
        nome: a.nome,
        treinos: a.treinos,
      })),
    };
  }

  async function salvar() {
    setErro("");
    if (form.aparelhos.length === 0) {
      setErro("Adicione ao menos um exercício (aparelho + treino) para registrar a aula.");
      return;
    }
    setLoading(true);
    try {
      const payload = montarPayload();
      if (editId) {
        await sessoesApi.update(clinic.id, aluno.id, editId, payload);
        setReadonly(true);
      } else {
        await sessoesApi.create(clinic.id, aluno.id, payload);
        setForm(vazio(profissionais));
        setEditId(null);
        setReadonly(false);
        setComboSel("");
      }
      await carregarAula(aluno);
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  }

  function consultar(s) {
    setErro("");
    setReadonly(true);
    setEditId(s.id);
    setComboSel("");
    setForm({
      data: s.data || hojeISO(),
      // Sem id mas com nome = aula antiga de texto livre: fica selecionada como
      // "registro antigo" até alguém escolher alguém do cadastro.
      profissionalId: s.profissionalId || (s.profissional ? LEGADO : ""),
      profissionalLegado: s.profissionalId ? "" : s.profissional || "",
      observacao: s.observacao || "",
      aparelhos: (s.aparelhos || []).map((a) => ({
        aparelhoId: a.aparelhoId || null,
        nome: a.nome,
        treinos: Array.isArray(a.treinos) ? a.treinos : [],
      })),
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function habilitarEdicao() {
    setReadonly(false);
  }

  function novaAula() {
    setForm(vazio(profissionais));
    setEditId(null);
    setReadonly(false);
    setComboSel("");
  }

  async function remover(s) {
    if (!confirm(`Remover a aula de ${formatDataBR(s.data)}?`)) return;
    setErro("");
    try {
      await sessoesApi.remove(clinic.id, aluno.id, s.id);
      if (editId === s.id) novaAula();
      await carregarAula(aluno);
    } catch (e) {
      setErro(e.message);
    }
  }

  // ---------- Tela 1: seleção do aluno ----------
  if (view === "lista") {
    const filtro = busca.trim().toLowerCase();
    const filtroDigits = onlyDigits(busca);
    const filtrados = filtro
      ? pacientes.filter(
          (p) =>
            (p.nome || "").toLowerCase().includes(filtro) ||
            (filtroDigits && onlyDigits(p.cpf || "").includes(filtroDigits)) ||
            (filtroDigits && onlyDigits(p.telefone || "").includes(filtroDigits))
        )
      : pacientes;

    return (
      <div>
        <div className="list-header">
          <input
            className="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Selecione o aluno para iniciar a aula (nome, CPF ou telefone)…"
          />
        </div>

        {erro && <div className="erro">{erro}</div>}

        <div className="card">
          <h2>Iniciar aula — escolha o aluno ({carregandoLista ? "…" : filtrados.length})</h2>
          {carregandoLista ? (
            <div className="loading">
              <span className="spinner" />
              Carregando alunos…
            </div>
          ) : pacientes.length === 0 ? (
            <p className="muted">
              Nenhum aluno cadastrado ainda. Cadastre um paciente na aba Pacientes.
            </p>
          ) : filtrados.length === 0 ? (
            <p className="muted">Nenhum aluno encontrado para “{busca}”.</p>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>CPF</th>
                  <th>Telefone</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((p) => (
                  <tr key={p.id} className="row-click" onClick={() => selecionarAluno(p)}>
                    <td>{p.nome}</td>
                    <td>{p.cpf ? maskCpf(p.cpf) : "—"}</td>
                    <td>{p.telefone || "—"}</td>
                    <td className="td-actions">
                      <span className="link">iniciar aula →</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    );
  }

  // ---------- Tela 2: workspace da aula ----------
  const semCatalogo = catalogo.length === 0;
  const nomeAtual = catalogo.find((a) => a.id === comboSel)?.nome || "";
  const treinosAtuais = form.aparelhos.find((a) => a.aparelhoId === comboSel)?.treinos || [];
  // lista plana de pares aparelho→treino (o "carrinho" da aula)
  const pares = form.aparelhos.flatMap((a) =>
    a.treinos.length
      ? a.treinos.map((t) => ({ aparelhoId: a.aparelhoId, nome: a.nome, treino: t }))
      : [{ aparelhoId: a.aparelhoId, nome: a.nome, treino: null }]
  );

  return (
    <div>
      <div className="crumbs">
        <button className="link" onClick={voltarLista}>← Alunos</button>
        <span className="muted"> / Aula de </span>
        <strong>{aluno?.nome}</strong>
      </div>

      <form onSubmit={(e) => e.preventDefault()}>
        <div className="grid">
          {/* Coluna 1: montar a aula */}
          <div className="card form">
            <h2>{!editId ? "Nova aula" : readonly ? "Aula" : "Editar aula"}</h2>
            {erro && <div className="erro">{erro}</div>}

            <fieldset className="fs-reset" disabled={readonly}>
              <div className="row">
                <div style={{ maxWidth: 180 }}>
                  <label>Data *</label>
                  <input
                    type="date"
                    value={form.data}
                    onChange={(e) => setCampo("data", e.target.value)}
                  />
                </div>
                <div>
                  <label>Profissional responsável</label>
                  <select
                    value={form.profissionalId}
                    onChange={(e) => setCampo("profissionalId", e.target.value)}
                  >
                    <option value="">— escolha o profissional —</option>
                    {form.profissionalId === LEGADO && (
                      <option value={LEGADO}>{form.profissionalLegado} (registro antigo)</option>
                    )}
                    {profissionais.map((p) => (
                      <option key={p.id} value={p.id}>{p.nome}</option>
                    ))}
                    {/* Profissional removido do cadastro: mantém o nome visível na aula. */}
                    {form.profissionalId &&
                      form.profissionalId !== LEGADO &&
                      !profissionais.some((p) => p.id === form.profissionalId) && (
                        <option value={form.profissionalId}>
                          {lista.find((s) => s.id === editId)?.profissional || "Profissional removido"}
                        </option>
                      )}
                  </select>
                  {profissionais.length === 0 && (
                    <small className="muted">
                      Cadastre os profissionais em Parametrização → Profissionais.
                    </small>
                  )}
                </div>
              </div>

              {!readonly && (
                <>
                  <div className="sep">Adicionar exercício</div>
                  {carregandoAula ? (
                    <div className="loading">
                      <span className="spinner" />
                      Carregando aparelhos…
                    </div>
                  ) : semCatalogo ? (
                    <div className="erro">
                      Nenhum aparelho cadastrado nesta clínica. Cadastre aparelhos na aba
                      Aparelhos antes de registrar a aula.
                    </div>
                  ) : (
                    <>
                      <label>Aparelho</label>
                      <select value={comboSel} onChange={(e) => setComboSel(e.target.value)}>
                        <option value="">— escolha um aparelho —</option>
                        {catalogo.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.nome}
                            {a.categoria ? ` (${a.categoria})` : ""}
                          </option>
                        ))}
                      </select>

                      {comboSel ? (
                        <>
                          <label>
                            Treinos de {nomeAtual}{" "}
                            <span className="opt">(clique para adicionar à lista)</span>
                          </label>
                          <div className="chips">
                            {TIPOS_TREINO.map((t) => {
                              const on = treinosAtuais.includes(t);
                              return (
                                <button
                                  key={t}
                                  type="button"
                                  className={on ? "chip on" : "chip"}
                                  onClick={() => toggleTreinoAtual(t)}
                                >
                                  {on ? "✓ " : "+ "}
                                  {t}
                                </button>
                              );
                            })}
                          </div>
                        </>
                      ) : (
                        <p className="muted" style={{ marginTop: 10 }}>
                          Escolha um aparelho e clique nos treinos para montar a aula.
                          Repita para adicionar outros aparelhos.
                        </p>
                      )}
                    </>
                  )}
                </>
              )}
            </fieldset>
          </div>

          {/* Coluna 2: lista de exercícios da aula (o "carrinho") */}
          <div className="card">
            <h2>Exercícios da aula ({pares.length})</h2>
            {pares.length === 0 ? (
              <p className="muted">
                Nenhum exercício adicionado ainda. Escolha um aparelho ao lado e clique nos
                treinos.
              </p>
            ) : (
              <ul className="pares">
                {pares.map((p, i) => (
                  <li key={`${p.aparelhoId}-${p.treino}-${i}`}>
                    <span>
                      <strong>{p.nome}</strong>
                      {" — "}
                      {p.treino || <em className="muted">sem treino</em>}
                    </span>
                    {!readonly && (
                      <button
                        type="button"
                        className="link danger"
                        title="Remover"
                        onClick={() => removerPar(p.aparelhoId, p.treino)}
                      >
                        ✕
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="card form obs-card">
          <fieldset className="fs-reset" disabled={readonly}>
            <div className="sep sep-top">Observação</div>
            <label>
              Observação <span className="opt">(anotações livres da aula)</span>
            </label>
            <textarea
              className="obs"
              rows={6}
              value={form.observacao}
              onChange={(e) => setCampo("observacao", e.target.value)}
              placeholder="Escreva aqui o que quiser sobre esta aula…"
            />
          </fieldset>
          <div className="actions">
            {readonly ? (
              <>
                <button key="editar" type="button" className="btn primary" onClick={habilitarEdicao}>
                  Editar
                </button>
                <button key="nova" type="button" className="btn" onClick={novaAula}>
                  Nova aula
                </button>
              </>
            ) : (
              <>
                <button
                  key="salvar"
                  type="button"
                  className="btn primary"
                  disabled={loading || semCatalogo}
                  onClick={salvar}
                >
                  {loading ? "Salvando..." : editId ? "Salvar" : "Salvar aula"}
                </button>
                {editId && (
                  <button key="cancelar" type="button" className="btn" onClick={novaAula}>
                    Cancelar
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </form>

      {/* Histórico de aulas do aluno */}
      <div className="card" style={{ marginTop: 20 }}>
        <h2>Aulas registradas ({carregandoAula ? "…" : lista.length})</h2>
        {carregandoAula ? (
          <div className="loading">
            <span className="spinner" />
            Carregando aulas…
          </div>
        ) : lista.length === 0 ? (
          <p className="muted">Nenhuma aula registrada para este aluno.</p>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Data</th>
                <th>Exercícios</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lista.map((s) => (
                <tr key={s.id}>
                  <td>{formatDataBR(s.data)}</td>
                  <td className="td-desc">
                    {(s.aparelhos || [])
                      .map((a) =>
                        a.treinos && a.treinos.length
                          ? `${a.nome} (${a.treinos.join(", ")})`
                          : a.nome
                      )
                      .join(" · ") || "—"}
                  </td>
                  <td className="td-actions">
                    <button type="button" className="link" onClick={() => consultar(s)}>
                      consultar
                    </button>
                    <button type="button" className="link danger" onClick={() => remover(s)}>
                      remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
