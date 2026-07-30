import { useState } from "react";
import { definirNovaSenha, login } from "../auth";
import logoUrl from "../assets/pilatesone-logo.jpg";

// Login real (M3/AUTH-05): e-mail + senha via Cognito. No 1º acesso (senha
// temporária) o Cognito exige definir uma nova senha antes de entrar.
function traduzErro(err) {
  switch (err.code) {
    case "NotAuthorizedException":
    case "UserNotFoundException":
      return "E-mail ou senha inválidos.";
    case "InvalidPasswordException":
      return "Senha fraca: use 8+ caracteres com maiúscula, minúscula e número.";
    case "UserNotConfirmedException":
      return "Usuário ainda não confirmado. Fale com o administrador.";
    default:
      return err.message || "Não foi possível entrar. Tente novamente.";
  }
}

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmaSenha, setConfirmaSenha] = useState("");
  const [challenge, setChallenge] = useState(null); // { session, email }
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function entrar(e) {
    e.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      const r = await login(email.trim().toLowerCase(), senha);
      if (r.challenge === "NEW_PASSWORD_REQUIRED") {
        setChallenge({ session: r.session, email: r.email });
      } else {
        onLogin(r.claims);
      }
    } catch (err) {
      setErro(traduzErro(err));
    } finally {
      setCarregando(false);
    }
  }

  async function trocarSenha(e) {
    e.preventDefault();
    setErro("");
    if (novaSenha !== confirmaSenha) {
      setErro("As senhas não coincidem.");
      return;
    }
    setCarregando(true);
    try {
      const r = await definirNovaSenha(challenge.email, challenge.session, novaSenha);
      onLogin(r.claims);
    } catch (err) {
      setErro(traduzErro(err));
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <img
          src={logoUrl}
          alt="Pilates One — Sistema completo para gestão do Pilates"
          className="login-logo"
        />

        {!challenge ? (
          <>
            <p className="muted login-sub">Entre com seu e-mail e senha</p>
            <form onSubmit={entrar} className="login-form">
              <input
                type="email"
                placeholder="E-mail"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Senha"
                autoComplete="current-password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
              />
              {erro && <p className="login-erro">{erro}</p>}
              <button className="btn primary" type="submit" disabled={carregando}>
                {carregando ? "Entrando…" : "Entrar"}
              </button>
            </form>
          </>
        ) : (
          <>
            <h1>Defina sua senha</h1>
            <p className="muted">Primeiro acesso: escolha uma senha definitiva.</p>
            <form onSubmit={trocarSenha} className="login-form">
              <input
                type="password"
                placeholder="Nova senha"
                autoComplete="new-password"
                value={novaSenha}
                onChange={(e) => setNovaSenha(e.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Confirme a nova senha"
                autoComplete="new-password"
                value={confirmaSenha}
                onChange={(e) => setConfirmaSenha(e.target.value)}
                required
              />
              {erro && <p className="login-erro">{erro}</p>}
              <button className="btn primary" type="submit" disabled={carregando}>
                {carregando ? "Salvando…" : "Salvar e entrar"}
              </button>
            </form>
          </>
        )}

        <p className="login-note muted">
          Acesso restrito à equipe. Cada clínica só enxerga os próprios dados.
        </p>
      </div>
    </div>
  );
}
