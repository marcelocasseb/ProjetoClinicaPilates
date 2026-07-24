import { useEffect, useState } from "react";
import { avaliacoesApi } from "../api";
import { hojeISO, formatDataBR } from "../utils/format";

function vazio() {
  return {
    data: hojeISO(),
    diagnosticoMedico: "",
    queixaPrincipal: "",
    hma: "",
    pressaoArterial: "",
    fc: "",
    avaliacaoPostural: {
      vistaAnterior: "",
      vistaLateralDireita: "",
      vistaLateralEsquerda: "",
      vistaPosterior: "",
    },
    medidas: { braco: "", abdomen: "", coxa: "", panturrilha: "" },
    inspecaoGeral: "",
    examesComplementares: "",
    observacao: "",
  };
}

// Converte um objeto de sub-campos em null se todos estiverem vazios.
function mapOuNull(obj) {
  const limpo = {};
  let algum = false;
  for (const [k, v] of Object.entries(obj)) {
    const t = (v || "").trim();
    limpo[k] = t || null;
    if (t) algum = true;
  }
  return algum ? limpo : null;
}

export default function Avaliacoes({ clinic, paciente, onVoltar, embedded = false }) {
  const [lista, setLista] = useState([]);
  const [form, setForm] = useState(vazio());
  const [editId, setEditId] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function carregar() {
    setErro("");
    try {
      setLista(await avaliacoesApi.list(clinic.id, paciente.id));
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    carregar();
    setForm(vazio());
    setEditId(null);
  }, [clinic.id, paciente.id]);

  function setCampo(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }
  function setPostural(campo, valor) {
    setForm((f) => ({ ...f, avaliacaoPostural: { ...f.avaliacaoPostural, [campo]: valor } }));
  }
  function setMedida(campo, valor) {
    setForm((f) => ({ ...f, medidas: { ...f.medidas, [campo]: valor } }));
  }

  function montarPayload() {
    const txt = (v) => (v && v.trim() ? v.trim() : null);
    return {
      data: form.data || null,
      diagnosticoMedico: txt(form.diagnosticoMedico),
      queixaPrincipal: txt(form.queixaPrincipal),
      hma: txt(form.hma),
      pressaoArterial: txt(form.pressaoArterial),
      fc: txt(form.fc),
      avaliacaoPostural: mapOuNull(form.avaliacaoPostural),
      medidas: mapOuNull(form.medidas),
      inspecaoGeral: txt(form.inspecaoGeral),
      examesComplementares: txt(form.examesComplementares),
      observacao: txt(form.observacao),
    };
  }

  async function salvar(e) {
    e.preventDefault();
    setErro("");
    setLoading(true);
    try {
      const payload = montarPayload();
      if (editId) await avaliacoesApi.update(clinic.id, paciente.id, editId, payload);
      else await avaliacoesApi.create(clinic.id, paciente.id, payload);
      setForm(vazio());
      setEditId(null);
      await carregar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  }

  function editar(a) {
    setEditId(a.id);
    setForm({
      data: a.data || hojeISO(),
      diagnosticoMedico: a.diagnosticoMedico || "",
      queixaPrincipal: a.queixaPrincipal || "",
      hma: a.hma || "",
      pressaoArterial: a.pressaoArterial || "",
      fc: a.fc || "",
      avaliacaoPostural: {
        vistaAnterior: a.avaliacaoPostural?.vistaAnterior || "",
        vistaLateralDireita: a.avaliacaoPostural?.vistaLateralDireita || "",
        vistaLateralEsquerda: a.avaliacaoPostural?.vistaLateralEsquerda || "",
        vistaPosterior: a.avaliacaoPostural?.vistaPosterior || "",
      },
      medidas: {
        braco: a.medidas?.braco || "",
        abdomen: a.medidas?.abdomen || "",
        coxa: a.medidas?.coxa || "",
        panturrilha: a.medidas?.panturrilha || "",
      },
      inspecaoGeral: a.inspecaoGeral || "",
      examesComplementares: a.examesComplementares || "",
      observacao: a.observacao || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remover(a) {
    if (!confirm(`Remover a avaliação de ${formatDataBR(a.data)}?`)) return;
    setErro("");
    try {
      await avaliacoesApi.remove(clinic.id, paciente.id, a.id);
      if (editId === a.id) {
        setForm(vazio());
        setEditId(null);
      }
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  function cancelar() {
    setForm(vazio());
    setEditId(null);
  }

  return (
    <div>
      {embedded ? (
        <div className="sep">Avaliações de {paciente.nome}</div>
      ) : (
        <div className="crumbs">
          <button className="link" onClick={onVoltar}>← Pacientes</button>
          <span className="muted"> / Avaliações de </span>
          <strong>{paciente.nome}</strong>
        </div>
      )}

      <form onSubmit={salvar}>
      <div className="grid">
        <div className="card form">
          <h2>{editId ? "Editar avaliação/consulta" : "Nova avaliação/consulta"}</h2>
          {erro && <div className="erro">{erro}</div>}

          <div className="row">
            <div style={{ maxWidth: 180 }}>
              <label>Data *</label>
              <input type="date" value={form.data} onChange={(e) => setCampo("data", e.target.value)} />
            </div>
          </div>

          <label>Diagnóstico médico</label>
          <textarea rows={2} value={form.diagnosticoMedico} onChange={(e) => setCampo("diagnosticoMedico", e.target.value)} />

          <label>Queixa principal</label>
          <textarea rows={2} value={form.queixaPrincipal} onChange={(e) => setCampo("queixaPrincipal", e.target.value)} />

          <label>HMA — História da Moléstia Atual</label>
          <textarea rows={2} value={form.hma} onChange={(e) => setCampo("hma", e.target.value)} />

          <div className="row">
            <div>
              <label>Pressão arterial</label>
              <input value={form.pressaoArterial} onChange={(e) => setCampo("pressaoArterial", e.target.value)} placeholder="12/8" />
            </div>
            <div>
              <label>FC — freq. cardíaca</label>
              <input value={form.fc} onChange={(e) => setCampo("fc", e.target.value)} placeholder="72 bpm" />
            </div>
          </div>

          <div className="sep">Avaliação postural</div>
          <label>Vista anterior</label>
          <textarea rows={2} value={form.avaliacaoPostural.vistaAnterior} onChange={(e) => setPostural("vistaAnterior", e.target.value)} />
          <div className="row">
            <div>
              <label>Vista lateral D</label>
              <textarea rows={2} value={form.avaliacaoPostural.vistaLateralDireita} onChange={(e) => setPostural("vistaLateralDireita", e.target.value)} />
            </div>
            <div>
              <label>Vista lateral E</label>
              <textarea rows={2} value={form.avaliacaoPostural.vistaLateralEsquerda} onChange={(e) => setPostural("vistaLateralEsquerda", e.target.value)} />
            </div>
          </div>
          <label>Vista posterior</label>
          <textarea rows={2} value={form.avaliacaoPostural.vistaPosterior} onChange={(e) => setPostural("vistaPosterior", e.target.value)} />

          <div className="sep">Medidas</div>
          <div className="row">
            <div>
              <label>Braço</label>
              <input value={form.medidas.braco} onChange={(e) => setMedida("braco", e.target.value)} placeholder="30 cm" />
            </div>
            <div>
              <label>Abdômen</label>
              <input value={form.medidas.abdomen} onChange={(e) => setMedida("abdomen", e.target.value)} placeholder="80 cm" />
            </div>
          </div>
          <div className="row">
            <div>
              <label>Coxa</label>
              <input value={form.medidas.coxa} onChange={(e) => setMedida("coxa", e.target.value)} placeholder="50 cm" />
            </div>
            <div>
              <label>Panturrilha</label>
              <input value={form.medidas.panturrilha} onChange={(e) => setMedida("panturrilha", e.target.value)} placeholder="35 cm" />
            </div>
          </div>

          <div className="sep">Inspeção geral e exames</div>
          <label>Inspeção geral <span className="opt">(flexibilidade, força, dor)</span></label>
          <textarea rows={2} value={form.inspecaoGeral} onChange={(e) => setCampo("inspecaoGeral", e.target.value)} />
          <label>Exames complementares ou testes</label>
          <textarea rows={2} value={form.examesComplementares} onChange={(e) => setCampo("examesComplementares", e.target.value)} />
        </div>

        <div className="card">
          <h2>Avaliações ({lista.length})</h2>
          {lista.length === 0 ? (
            <p className="muted">Nenhuma avaliação registrada para este paciente.</p>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Queixa principal</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lista.map((a) => (
                  <tr key={a.id}>
                    <td>{formatDataBR(a.data)}</td>
                    <td className="td-desc">{a.queixaPrincipal || "—"}</td>
                    <td className="td-actions">
                      <button className="link" onClick={() => editar(a)}>editar</button>
                      <button className="link danger" onClick={() => remover(a)}>remover</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card form obs-card">
        <div className="sep sep-top">Observação</div>
        <label>
          Observação <span className="opt">(anotações livres da consulta/sessão)</span>
        </label>
        <textarea
          className="obs"
          rows={7}
          value={form.observacao}
          onChange={(e) => setCampo("observacao", e.target.value)}
          placeholder="Escreva aqui o que quiser sobre esta consulta/avaliação…"
        />
        <div className="actions">
          <button type="submit" className="btn primary" disabled={loading}>
            {loading ? "Salvando..." : editId ? "Salvar" : "Salvar avaliação"}
          </button>
          {editId && (
            <button type="button" className="btn" onClick={cancelar}>Cancelar</button>
          )}
        </div>
      </div>
      </form>
    </div>
  );
}
