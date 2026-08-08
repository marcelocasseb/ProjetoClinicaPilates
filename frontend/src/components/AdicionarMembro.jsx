import { useState } from "react";
import { membrosApi } from "../api";

// Modal do admin para adicionar um membro da equipe (AUTH-07). O membro herda a
// clínica do token do admin (o front não envia clinicId). A senha temporária é
// exibida ao admin para repasse fora de banda (D2) — o Cognito não manda e-mail.
export default function AdicionarMembro({ onFechar }) {
  const [email, setEmail] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [criado, setCriado] = useState(null); // { email, senha_temporaria }

  async function criar(e) {
    e.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      const res = await membrosApi.create({ email: email.trim().toLowerCase() });
      setCriado(res);
    } catch (err) {
      setErro(err.message || "Não foi possível criar o membro.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onFechar}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>Adicionar membro</h2>

        {!criado ? (
          <form onSubmit={criar}>
            <p className="muted">
              Informe o e-mail. Ele nasce na sua clínica e define a senha no 1º acesso.
            </p>
            <input
              type="email"
              placeholder="E-mail do membro"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            {erro && <p className="login-erro">{erro}</p>}
            <div className="modal-actions">
              <button type="button" className="btn ghost" onClick={onFechar}>
                Cancelar
              </button>
              <button type="submit" className="btn primary" disabled={carregando}>
                {carregando ? "Criando…" : "Criar membro"}
              </button>
            </div>
          </form>
        ) : (
          <div>
            <p>
              Membro <strong>{criado.email}</strong> criado. Repasse a senha temporária
              (o sistema não envia e-mail):
            </p>
            <p className="senha-temp">{criado.senha_temporaria}</p>
            <p className="muted">
              No 1º login o membro será obrigado a definir uma senha própria.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn primary" onClick={onFechar}>
                Concluir
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
