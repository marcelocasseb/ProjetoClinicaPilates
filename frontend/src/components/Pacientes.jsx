import { useEffect, useState } from "react";
import { pacientesApi, buscarCep } from "../api";
import { maskCpf, maskTelefone, maskCep, isValidCpf, onlyDigits } from "../utils/format";
import Avaliacoes from "./Avaliacoes";

const VAZIO = {
  nome: "",
  cpf: "",
  telefone: "",
  email: "",
  endereco: { cep: "", logradouro: "", numero: "", bairro: "", cidade: "", uf: "" },
};

export default function Pacientes({ clinic }) {
  const [lista, setLista] = useState([]);
  const [busca, setBusca] = useState("");
  const [view, setView] = useState("lista"); // "lista" (consulta) | "detalhe" (ficha)
  const [selecionado, setSelecionado] = useState(null); // paciente aberto na ficha (com id/nome)
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
    setView("lista");
    setBusca("");
    setForm(VAZIO);
    setEditId(null);
    setSelecionado(null);
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

  function preencherForm(p) {
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
  }

  // Abre a ficha de um paciente existente (consulta/edição + avaliações).
  function abrirPaciente(p) {
    setErro("");
    setEditId(p.id);
    setSelecionado(p);
    preencherForm(p);
    setView("detalhe");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Abre a ficha vazia para cadastrar um novo paciente.
  function abrirNovo() {
    setErro("");
    setEditId(null);
    setSelecionado(null);
    setForm(VAZIO);
    setView("detalhe");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function voltarLista() {
    setView("lista");
    setErro("");
    setForm(VAZIO);
    setEditId(null);
    setSelecionado(null);
    carregar();
  }

  async function salvar(e) {
    e.preventDefault();
    if (cpfInvalido) return;
    setErro("");
    setLoading(true);
    try {
      const payload = montarPayload();
      if (editId) {
        const atualizado = await pacientesApi.update(clinic.id, editId, payload);
        setSelecionado(atualizado);
      } else {
        // Após criar, permanece na ficha já em modo edição para liberar as avaliações.
        const criado = await pacientesApi.create(clinic.id, payload);
        setEditId(criado.id);
        setSelecionado(criado);
        preencherForm(criado);
      }
      await carregar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function remover(p) {
    if (!confirm(`Remover o paciente "${p.nome}"?`)) return;
    setErro("");
    try {
      await pacientesApi.remove(clinic.id, p.id);
      voltarLista();
    } catch (e) {
      setErro(e.message);
    }
  }

  // ---------- Tela 1: consulta de pacientes ----------
  if (view === "lista") {
    const filtro = busca.trim().toLowerCase();
    const filtroDigits = onlyDigits(busca);
    const filtrados = filtro
      ? lista.filter(
          (p) =>
            (p.nome || "").toLowerCase().includes(filtro) ||
            (filtroDigits && onlyDigits(p.cpf || "").includes(filtroDigits)) ||
            (filtroDigits && onlyDigits(p.telefone || "").includes(filtroDigits))
        )
      : lista;

    return (
      <div>
        <div className="list-header">
          <input
            className="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Pesquisar paciente por nome, CPF ou telefone…"
          />
          <button className="btn primary" onClick={abrirNovo}>
            + Adicionar paciente
          </button>
        </div>

        {erro && <div className="erro">{erro}</div>}

        <div className="card">
          <h2>Pacientes ({filtrados.length})</h2>
          {lista.length === 0 ? (
            <p className="muted">Nenhum paciente cadastrado ainda.</p>
          ) : filtrados.length === 0 ? (
            <p className="muted">Nenhum paciente encontrado para “{busca}”.</p>
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
                {filtrados.map((p) => (
                  <tr key={p.id} className="row-click" onClick={() => abrirPaciente(p)}>
                    <td>{p.nome}</td>
                    <td>{p.cpf ? maskCpf(p.cpf) : "—"}</td>
                    <td>{p.telefone || "—"}</td>
                    <td>{p.endereco?.cidade || "—"}</td>
                    <td className="td-actions">
                      <span className="link">abrir ficha →</span>
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

  // ---------- Tela 2: ficha do paciente (dados + avaliações) ----------
  return (
    <div>
      <div className="crumbs">
        <button className="link" onClick={voltarLista}>← Pacientes</button>
        <span className="muted"> / </span>
        <strong>{editId ? selecionado?.nome || "Ficha do paciente" : "Novo paciente"}</strong>
      </div>

      <form className="card form" style={{ maxWidth: 640 }} onSubmit={salvar}>
        <h2>{editId ? "Dados do paciente" : "Novo paciente"}</h2>
        {erro && <div className="erro">{erro}</div>}

        <label>Nome *</label>
        <input value={form.nome} onChange={(e) => setCampo("nome", e.target.value)} placeholder="Nome do paciente" />

        <div className="row">
          <div>
            <label>CPF <span className="opt">(opcional)</span></label>
            <input
              className={cpfInvalido ? "input-erro" : ""}
              value={form.cpf}
              onChange={(e) => setCampo("cpf", maskCpf(e.target.value))}
              placeholder="000.000.000-00"
              inputMode="numeric"
            />
            {cpfInvalido && <small className="campo-erro">CPF inválido — confira os dígitos (ou deixe em branco)</small>}
          </div>
          <div>
            <label>Telefone <span className="opt">(opcional)</span></label>
            <input
              value={form.telefone}
              onChange={(e) => setCampo("telefone", maskTelefone(e.target.value))}
              placeholder="(11) 90000-0000"
              inputMode="numeric"
            />
          </div>
        </div>

        <label>E-mail <span className="opt">(opcional)</span></label>
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
          <button type="button" className="btn" onClick={voltarLista}>
            Voltar
          </button>
          {editId && (
            <button type="button" className="btn" style={{ marginLeft: "auto" }} onClick={() => remover(selecionado)}>
              Remover paciente
            </button>
          )}
        </div>
      </form>

      {selecionado ? (
        <div style={{ marginTop: 28 }}>
          <Avaliacoes clinic={clinic} paciente={selecionado} embedded />
        </div>
      ) : (
        <p className="muted" style={{ marginTop: 20 }}>
          Salve o paciente para registrar avaliações.
        </p>
      )}
    </div>
  );
}
