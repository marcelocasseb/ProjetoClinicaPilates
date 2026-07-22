import { useEffect, useState } from "react";
import { pacientesApi, buscarCep } from "../api";
import { maskCpf, maskTelefone, maskCep, isValidCpf, onlyDigits } from "../utils/format";

const VAZIO = {
  nome: "",
  cpf: "",
  telefone: "",
  email: "",
  endereco: { cep: "", logradouro: "", numero: "", bairro: "", cidade: "", uf: "" },
};

export default function Pacientes({ clinic }) {
  const [lista, setLista] = useState([]);
  const [form, setForm] = useState(VAZIO);
  const [editId, setEditId] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function carregar() {
    setErro("");
    try {
      setLista(await pacientesApi.list(clinic.id));
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
  function setEndereco(campo, valor) {
    setForm((f) => ({ ...f, endereco: { ...f.endereco, [campo]: valor } }));
  }

  // CEP: mascara e, ao completar 8 dígitos, busca e preenche o endereço.
  async function onCepChange(valor) {
    const mascarado = maskCep(valor);
    setEndereco("cep", mascarado);
    if (onlyDigits(mascarado).length === 8) {
      const achado = await buscarCep(mascarado);
      if (achado) {
        setForm((f) => ({
          ...f,
          endereco: { ...f.endereco, ...achado, cep: maskCep(achado.cep), numero: f.endereco.numero },
        }));
      }
    }
  }

  const cpfDigits = onlyDigits(form.cpf);
  const cpfInvalido = cpfDigits.length === 11 && !isValidCpf(cpfDigits);

  function montarPayload() {
    const end = form.endereco;
    const temEndereco = Object.values(end).some((v) => v && v.trim());
    return {
      nome: form.nome,
      cpf: cpfDigits || null,
      telefone: form.telefone || null,
      email: form.email || null,
      endereco: temEndereco ? { ...end, cep: onlyDigits(end.cep) || null } : null,
    };
  }

  async function salvar(e) {
    e.preventDefault();
    if (cpfInvalido) return;
    setErro("");
    setLoading(true);
    try {
      const payload = montarPayload();
      if (editId) await pacientesApi.update(clinic.id, editId, payload);
      else await pacientesApi.create(clinic.id, payload);
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
    setForm({
      nome: p.nome || "",
      cpf: maskCpf(p.cpf || ""),
      telefone: maskTelefone(p.telefone || ""),
      email: p.email || "",
      endereco: {
        cep: maskCep(p.endereco?.cep || ""),
        logradouro: p.endereco?.logradouro || "",
        numero: p.endereco?.numero || "",
        bairro: p.endereco?.bairro || "",
        cidade: p.endereco?.cidade || "",
        uf: p.endereco?.uf || "",
      },
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remover(p) {
    if (!confirm(`Remover o paciente "${p.nome}"?`)) return;
    setErro("");
    try {
      await pacientesApi.remove(clinic.id, p.id);
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
        <h2>{editId ? "Editar paciente" : "Novo paciente"}</h2>
        {erro && <div className="erro">{erro}</div>}

        <label>Nome *</label>
        <input value={form.nome} onChange={(e) => setCampo("nome", e.target.value)} placeholder="Nome do paciente" />

        <div className="row">
          <div>
            <label>CPF</label>
            <input
              className={cpfInvalido ? "input-erro" : ""}
              value={form.cpf}
              onChange={(e) => setCampo("cpf", maskCpf(e.target.value))}
              placeholder="000.000.000-00"
              inputMode="numeric"
            />
            {cpfInvalido && <small className="campo-erro">CPF inválido</small>}
          </div>
          <div>
            <label>Telefone</label>
            <input
              value={form.telefone}
              onChange={(e) => setCampo("telefone", maskTelefone(e.target.value))}
              placeholder="(11) 90000-0000"
              inputMode="numeric"
            />
          </div>
        </div>

        <label>E-mail</label>
        <input value={form.email} onChange={(e) => setCampo("email", e.target.value)} placeholder="email@exemplo.com" />

        <div className="sep">Endereço</div>
        <div className="row">
          <div>
            <label>CEP</label>
            <input
              value={form.endereco.cep}
              onChange={(e) => onCepChange(e.target.value)}
              placeholder="00000-000"
              inputMode="numeric"
            />
          </div>
          <div>
            <label>Número</label>
            <input value={form.endereco.numero} onChange={(e) => setEndereco("numero", e.target.value)} placeholder="123" />
          </div>
        </div>
        <label>Logradouro</label>
        <input value={form.endereco.logradouro} onChange={(e) => setEndereco("logradouro", e.target.value)} placeholder="preenchido pelo CEP" />
        <div className="row">
          <div>
            <label>Bairro</label>
            <input value={form.endereco.bairro} onChange={(e) => setEndereco("bairro", e.target.value)} />
          </div>
          <div>
            <label>Cidade</label>
            <input value={form.endereco.cidade} onChange={(e) => setEndereco("cidade", e.target.value)} />
          </div>
          <div style={{ maxWidth: 80 }}>
            <label>UF</label>
            <input value={form.endereco.uf} onChange={(e) => setEndereco("uf", e.target.value)} maxLength={2} />
          </div>
        </div>

        <div className="actions">
          <button type="submit" className="btn primary" disabled={loading || cpfInvalido}>
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
        <h2>Pacientes ({lista.length})</h2>
        {lista.length === 0 ? (
          <p className="muted">Nenhum paciente cadastrado ainda.</p>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Nome</th>
                <th>CPF</th>
                <th>Telefone</th>
                <th>Cidade</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lista.map((p) => (
                <tr key={p.id}>
                  <td>{p.nome}</td>
                  <td>{p.cpf ? maskCpf(p.cpf) : "—"}</td>
                  <td>{p.telefone || "—"}</td>
                  <td>{p.endereco?.cidade || "—"}</td>
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
