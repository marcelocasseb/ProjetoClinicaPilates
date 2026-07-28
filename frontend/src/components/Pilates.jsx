import { useEffect, useState } from "react";
import { pacientesApi, aparelhosApi, sessoesApi } from "../api";
import { onlyDigits, maskCpf, hojeISO, formatDataBR } from "../utils/format";

// Tipos de treino — lista fixa (hardcode no front, AD-011). O back só guarda o texto.
const TIPOS_TREINO = [
  "Membros superiores",
  "Membros inferiores",
  "Abdômen",
  "Força",
  "Mobilidade",
];

function vazio() {
  return { data: hojeISO(), profissional: "", observacao: "", aparelhos: [] };
}

export default function Pilates({ clinic }) {
  const [pacientes, setPacientes] = useState([]);
  const [busca, setBusca] = useState("");
  const [view, setView] = useState("lista"); // "lista" (seleção do aluno) | "aula"
  const [aluno, setAluno] = useState(null);

  const [catalogo, setCatalogo] = useState([]); // aparelhos ativos da clínica
  const [lista, setLista] = useState([]); // aulas do aluno
  const [form, setForm] = useState(vazio());
  const [editId, setEditId] = useState(null);
  const [readonly, setReadonly] = useState(false);
  const [comboSel, setComboSel] = useState(""); // aparelho escolhido no combo (antes de adicionar)
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function carregarPacientes() {
    setErro("");
    try {
      setPacientes(await pacientesApi.list(clinic.id));
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    carregarPacientes();
    setView("lista");
    setBusca("");
    setAluno(null);
  }, [clinic.id]);

  async function carregarAula(p) {
    setErro("");
    try {
      const [cat, aulas] = await Promise.all([
        aparelhosApi.list(clinic.id),
        sessoesApi.list(clinic.id, p.id),
      ]);
      setCatalogo(cat);
      setLista(aulas);
    } catch (e) {
      setErro(e.message);
    }
  }

  function selecionarAluno(p) {
    setAluno(p);
    setForm(vazio());
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
    setForm(vazio());
    setEditId(null);
    setReadonly(false);
    setErro("");
    carregarPacientes();
  }

  // ---- edição do form da aula ----
  function setCampo(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  function adicionarAparelho() {
    if (!comboSel) return;
    const ap = catalogo.find((a) => a.id === comboSel);
    if (!ap) return;
    if (form.aparelhos.some((a) => a.aparelhoId === ap.id)) {
      setComboSel("");
      return; // já está na aula
    }
    setForm((f) => ({
      ...f,
      aparelhos: [...f.aparelhos, { aparelhoId: ap.id, nome: ap.nome, treinos: [] }],
    }));
    setComboSel("");
  }

  function removerAparelho(idx) {
    setForm((f) => ({ ...f, aparelhos: f.aparelhos.filter((_, i) => i !== idx) }));
  }

  function toggleTreino(idx, treino) {
    setForm((f) => ({
      ...f,
      aparelhos: f.aparelhos.map((a, i) => {
        if (i !== idx) return a;
        const tem = a.treinos.includes(treino);
        return {
          ...a,
          treinos: tem ? a.treinos.filter((t) => t !== treino) : [...a.treinos, treino],
        };
      }),
    }));
  }

  function montarPayload() {
    const txt = (v) => (v && v.trim() ? v.trim() : null);
    return {
      data: form.data || null,
      profissional: txt(form.profissional),
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
      setErro("Adicione ao menos um aparelho para registrar a aula.");
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
        setForm(vazio());
        setEditId(null);
        setReadonly(false);
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
    setForm({
      data: s.data || hojeISO(),
      profissional: s.profissional || "",
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
    setForm(vazio());
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
          <h2>Iniciar aula — escolha o aluno ({filtrados.length})</h2>
          {pacientes.length === 0 ? (
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
  // O combo lista TODOS os aparelhos da clínica (os já adicionados continuam na
  // lista, marcados/desabilitados). `jaNaAula` = o item selecionado já foi adicionado.
  const jaNaAula = !!comboSel && form.aparelhos.some((x) => x.aparelhoId === comboSel);

  return (
    <div>
      <div className="crumbs">
        <button className="link" onClick={voltarLista}>← Alunos</button>
        <span className="muted"> / Aula de </span>
        <strong>{aluno?.nome}</strong>
      </div>

      <form onSubmit={(e) => e.preventDefault()}>
        <div className="grid">
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
                  <input
                    value={form.profissional}
                    onChange={(e) => setCampo("profissional", e.target.value)}
                    placeholder="Nome de quem conduziu a aula"
                  />
                </div>
              </div>

              <div className="sep">Aparelhos e treinos</div>

              {semCatalogo ? (
                <div className="erro">
                  Nenhum aparelho cadastrado nesta clínica. Cadastre aparelhos na aba
                  Aparelhos antes de registrar a aula.
                </div>
              ) : (
                <div className="row" style={{ alignItems: "flex-end" }}>
                  <div>
                    <label>
                      Adicionar aparelho <span className="opt">(pode adicionar vários)</span>
                    </label>
                    <select value={comboSel} onChange={(e) => setComboSel(e.target.value)}>
                      <option value="">— escolha um aparelho —</option>
                      {catalogo.map((a) => {
                        const add = form.aparelhos.some((x) => x.aparelhoId === a.id);
                        return (
                          <option key={a.id} value={a.id} disabled={add}>
                            {a.nome}
                            {a.categoria ? ` (${a.categoria})` : ""}
                            {add ? " — já na aula" : ""}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                  <div style={{ flex: "0 0 auto" }}>
                    <button
                      type="button"
                      className="btn primary"
                      onClick={adicionarAparelho}
                      disabled={!comboSel || jaNaAula}
                    >
                      + Adicionar
                    </button>
                  </div>
                </div>
              )}

              {form.aparelhos.length === 0 ? (
                <p className="muted">Nenhum aparelho adicionado à aula ainda.</p>
              ) : (
                <div className="aparelhos-aula">
                  {form.aparelhos.map((a, idx) => (
                    <div className="aparelho-item" key={`${a.aparelhoId || a.nome}-${idx}`}>
                      <div className="aparelho-head">
                        <strong>{a.nome}</strong>
                        {!readonly && (
                          <button
                            type="button"
                            className="link danger"
                            onClick={() => removerAparelho(idx)}
                          >
                            remover
                          </button>
                        )}
                      </div>
                      <div className="chips">
                        {TIPOS_TREINO.map((t) => {
                          const on = a.treinos.includes(t);
                          return (
                            <button
                              key={t}
                              type="button"
                              className={on ? "chip on" : "chip"}
                              onClick={() => !readonly && toggleTreino(idx, t)}
                              disabled={readonly}
                            >
                              {t}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </fieldset>
          </div>

          <div className="card">
            <h2>Aulas ({lista.length})</h2>
            {lista.length === 0 ? (
              <p className="muted">Nenhuma aula registrada para este aluno.</p>
            ) : (
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Aparelhos</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {lista.map((s) => (
                    <tr key={s.id}>
                      <td>{formatDataBR(s.data)}</td>
                      <td className="td-desc">
                        {(s.aparelhos || []).map((a) => a.nome).join(", ") || "—"}
                      </td>
                      <td className="td-actions">
                        <button type="button" className="link" onClick={() => consultar(s)}>
                          consultar
                        </button>
                        <button
                          type="button"
                          className="link danger"
                          onClick={() => remover(s)}
                        >
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
    </div>
  );
}
