import { useEffect, useState } from "react";
import { profissionaisApi } from "../api";
import { maskTelefone } from "../utils/format";

// Cadastro de profissionais da clínica (Parametrização → Profissionais). É a lista
// usada na Agenda e na aula do Pilates. Cada clínica tem a sua: o backend grava e
// lê sempre na clínica do login (o clinicId vem do token, nunca da tela).

const VAZIO = { nome: "", telefone: "" };

export default function Profissionais({ clinic }) {
  const [lista, setLista] = useState([]);
  const [form, setForm] = useState(VAZIO);
  const [editId, setEditId] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);
  const [carregandoLista, setCarregandoLista] = useState(true);

  async function carregar() {
    setErro("");
    setCarregandoLista(true);
    try {
      setLista(await profissionaisApi.list(clinic.id));
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregandoLista(false);
    }
  }

  useEffect(() => {
    carregar();
    setForm(VAZIO);
    setEditId(null);
  }, [clinic.id]);

  function setCampo(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  async function salvar(e) {
    e.preventDefault();
    setErro("");
    setLoading(true);
    try {
      const payload = { nome: form.nome, telefone: form.telefone || null };
      if (editId) await profissionaisApi.update(clinic.id, editId, payload);
      else await profissionaisApi.create(clinic.id, payload);
      setForm(VAZIO);
      setEditId(null);
      await carregar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  }

  function editar(p) {
    setEditId(p.id);
    setForm({ nome: p.nome || "", telefone: p.telefone || "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remover(p) {
    if (
      !confirm(
        `Remover "${p.nome}"? Ele sai das listas da Agenda e do Pilates, mas as marcações e aulas antigas continuam mostrando o nome.`
      )
    )
      return;
    setErro("");
    try {
      await profissionaisApi.remove(clinic.id, p.id);
      if (editId === p.id) cancelar();
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  function cancelar() {
    setForm(VAZIO);
    setEditId(null);
  }

  return (
    <div className="grid">
      <form className="card form" onSubmit={salvar}>
        <h2>{editId ? "Editar profissional" : "Novo profissional"}</h2>
        {erro && <div className="erro">{erro}</div>}

        <label>Nome *</label>
        <input
          value={form.nome}
          maxLength={120}
          onChange={(e) => setCampo("nome", e.target.value)}
          placeholder="Ex.: Dra. Ana Lima"
        />

        <label>Telefone</label>
        <input
          value={form.telefone}
          inputMode="tel"
          onChange={(e) => setCampo("telefone", maskTelefone(e.target.value))}
          placeholder="(00) 00000-0000"
        />

        <div className="actions">
          <button type="submit" className="btn primary" disabled={loading || !form.nome.trim()}>
            {loading ? "Salvando..." : editId ? "Salvar" : "Cadastrar"}
          </button>
          {editId && (
            <button type="button" className="btn" onClick={cancelar}>
              Cancelar
            </button>
          )}
        </div>
        <p className="muted prof-dica">
          Os profissionais cadastrados aqui aparecem para escolha na Agenda e na aula do Pilates.
        </p>
      </form>

      <div className="card">
        <h2>Profissionais ({carregandoLista ? "…" : lista.length})</h2>
        {carregandoLista ? (
          <div className="loading">
            <span className="spinner" />
            Carregando profissionais…
          </div>
        ) : lista.length === 0 ? (
          <p className="muted">Nenhum profissional cadastrado ainda.</p>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Telefone</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lista.map((p) => (
                <tr key={p.id}>
                  <td>{p.nome}</td>
                  <td>{p.telefone || "—"}</td>
                  <td className="td-actions">
                    <button className="link" onClick={() => editar(p)}>editar</button>
                    <button className="link danger" onClick={() => remover(p)}>remover</button>
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
