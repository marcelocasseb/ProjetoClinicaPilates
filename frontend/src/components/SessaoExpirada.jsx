import { useState } from "react";
import { getClaims, login } from "../auth";

// Modal de re-login exibido POR CIMA da tela de trabalho quando a sessão não
// pôde ser renovada em silêncio. O ponto central é não desmontar nada: o que o
// usuário estava digitando (ficha de avaliação, cadastro) continua intacto atrás
// do modal, e a requisição que tomou 401 é reenviada sozinha após o login.
//
// Antes disso, api.js fazia `window.location.reload()` aqui — e todo o
// formulário preenchido ia embora sem aviso.
export default function SessaoExpirada({ onEntrar, onSair }) {
  // Sabemos quem é pelas claims guardadas (o token venceu, mas continua legível),
  // então só pedimos a senha. Se por algum motivo não houver e-mail, o campo abre
  // para digitação em vez de travar o usuário.
  const emailSalvo = getClaims()?.email || "";
  const [email, setEmail] = useState(emailSalvo);
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function entrar(e) {
    e.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      const r = await login(email.trim().toLowerCase(), senha);
      // Senha temporária/expirada exige o fluxo completo — não dá para resolver
      // aqui dentro; manda para a tela de login (a perda é inevitável nesse caso).
      if (r.challenge) {
        onSair();
        return;
      }
      onEntrar(r.claims);
    } catch (err) {
      setErro(
        err.code === "NotAuthorizedException"
          ? "Senha incorreta."
          : err.message || "Não foi possível entrar."
      );
    } finally {
      setCarregando(false);
    }
  }

  return (
    // Sem onClick de fechar no overlay: clicar fora não pode abandonar a
    // requisição pendurada nem dar a impressão de que o trabalho foi salvo.
    <div className="modal-overlay">
      <div className="modal-card">
        <h2>Sua sessão expirou</h2>
        <p className="muted">
          Nada do que você preencheu foi perdido — está tudo aí atrás. Confirme sua
          senha para continuar de onde parou.
        </p>

        <form onSubmit={entrar}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            readOnly={Boolean(emailSalvo)}
            autoComplete="username"
            required
          />
          <input
            type="password"
            placeholder="Senha"
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoFocus
            required
          />
          {erro && <p className="login-erro">{erro}</p>}
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onSair}>
              Sair
            </button>
            <button type="submit" className="btn primary" disabled={carregando}>
              {carregando ? "Entrando…" : "Continuar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
