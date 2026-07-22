import { CLINICS } from "../config";

// Login simples do demo: escolher a clínica. (No M3 vira login real via Cognito.)
export default function Login({ onSelect }) {
  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="brand">
          <span className="brand-dot" />
          Clínica de Pilates
        </div>
        <h1>Bem-vindo(a)</h1>
        <p className="muted">Selecione sua clínica para entrar</p>

        <div className="clinic-list">
          {CLINICS.map((c) => (
            <button key={c.id} className="clinic-btn" onClick={() => onSelect(c)}>
              <span className="clinic-avatar">{c.nome.charAt(0)}</span>
              <span>
                <strong>{c.nome}</strong>
                <small className="muted">{c.id}</small>
              </span>
              <span className="chevron">→</span>
            </button>
          ))}
        </div>

        <p className="login-note muted">
          Demo — o login definitivo (Cognito) chega depois. Cada clínica só enxerga os próprios dados.
        </p>
      </div>
    </div>
  );
}
