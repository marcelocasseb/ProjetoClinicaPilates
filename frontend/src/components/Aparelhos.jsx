import { useEffect, useState } from "react";
import { aparelhosApi } from "../api";

const VAZIO = { nome: "", categoria: "", descricao: "" };

export default function Aparelhos({ clinic }) {
  const [lista, setLista] = useState([]);
  const [form, setForm] = useState(VAZIO);
  const [editId, setEditId] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function carregar() {
    setErro("");
    try {
      setLista(await aparelhosApi.list(clinic.id));
    } catch (e) {
      setErro(e.message);
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
      const payload = {
        nome: form.nome,
        categoria: form.categoria || null,
        descricao: form.descricao || null,
      };
      if (editId) await aparelhosApi.update(clinic.id, editId, payload);
      else await aparelhosApi.create(clinic.id, payload);
      setForm(VAZIO);
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
    setForm({ nome: a.nome || "", categoria: a.categoria || "", descricao: a.descricao || "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remover(a) {
    if (!confirm(`Remover o aparelho "${a.nome}"?`)) return;
    setErro("");
    try {
      await aparelhosApi.remove(clinic.id, a.id);
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
        <h2>{editId ? "Editar aparelho" : "Novo aparelho"}</h2>
        {erro && <div className="erro">{erro}</div>}

        <label>Nome *</label>
        <input value={form.nome} onChange={(e) => setCampo("nome", e.target.value)} placeholder="Ex.: Reformer" />

        <label>Categoria</label>
        <input value={form.categoria} onChange={(e) => setCampo("categoria", e.target.value)} placeholder="Ex.: Reformer, Cadillac, Chair..." />

        <label>Descrição</label>
        <textarea value={form.descricao} onChange={(e) => setCampo("descricao", e.target.value)} rows={3} placeholder="Observações (opcional)" />

        <div className="actions">
          <button type="submit" className="btn primary" disabled={loading}>
            {loading ? "Salvando..." : editId ? "Salvar" : "Cadastrar"}
          </button>
          {editId && (
            <button type="button" className="btn" onClick={cancelar}>
              Cancelar
            </button>
          )}
        </div>
      </form>

      <div className="card">
        <h2>Aparelhos ({lista.length})</h2>
        {lista.length === 0 ? (
          <p className="muted">Nenhum aparelho cadastrado ainda.</p>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Categoria</th>
                <th>Descrição</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lista.map((a) => (
                <tr key={a.id}>
                  <td>{a.nome}</td>
                  <td>{a.categoria || "—"}</td>
                  <td className="td-desc">{a.descricao || "—"}</td>
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
  );
}
