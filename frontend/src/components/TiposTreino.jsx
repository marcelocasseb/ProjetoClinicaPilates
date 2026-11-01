import { useEffect, useState } from "react";
import { tiposTreinoApi } from "../api";

// Cadastro dos tipos de treino da clínica (Parametrização → Tipos de treino). São os
// botões de treino da aula do Pilates. A aula guarda o texto do treino, então
// renomear ou remover aqui não altera as aulas já registradas.

const VAZIO = { nome: "" };

export default function TiposTreino({ clinic }) {
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
      setLista(await tiposTreinoApi.list(clinic.id));
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

  async function salvar(e) {
    e.preventDefault();
    setErro("");
    setLoading(true);
    try {
      const payload = { nome: form.nome };
      if (editId) await tiposTreinoApi.update(clinic.id, editId, payload);
      else await tiposTreinoApi.create(clinic.id, payload);
      setForm(VAZIO);
      setEditId(null);
      await carregar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  }

  function editar(t) {
    setEditId(t.id);
    setForm({ nome: t.nome || "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remover(t) {
    if (
      !confirm(
        `Remover "${t.nome}"? Ele sai dos treinos da aula, mas as aulas antigas continuam mostrando o nome.`
      )
    )
      return;
    setErro("");
    try {
      await tiposTreinoApi.remove(clinic.id, t.id);
      if (editId === t.id) cancelar();
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
        <h2>{editId ? "Editar tipo de treino" : "Novo tipo de treino"}</h2>
        {erro && <div className="erro">{erro}</div>}

        <label>Nome *</label>
        <input
          value={form.nome}
          maxLength={60}
          onChange={(e) => setForm({ nome: e.target.value })}
          placeholder="Ex.: Respiração"
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
          Os tipos cadastrados aqui aparecem como botões de treino na aula do Pilates, para
          qualquer aparelho. Renomear ou remover não altera as aulas já registradas.
        </p>
      </form>

      <div className="card">
        <h2>Tipos de treino ({carregandoLista ? "…" : lista.length})</h2>
        {carregandoLista ? (
          <div className="loading">
            <span className="spinner" />
            Carregando tipos de treino…
          </div>
        ) : lista.length === 0 ? (
          <p className="muted">Nenhum tipo de treino cadastrado.</p>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Nome</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lista.map((t) => (
                <tr key={t.id}>
                  <td>{t.nome}</td>
                  <td className="td-actions">
                    <button className="link" onClick={() => editar(t)}>editar</button>
                    <button className="link danger" onClick={() => remover(t)}>remover</button>
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
