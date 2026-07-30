import { useEffect, useState } from "react";
import Login from "./components/Login";
import Pacientes from "./components/Pacientes";
import Aparelhos from "./components/Aparelhos";
import Pilates from "./components/Pilates";
import AdicionarMembro from "./components/AdicionarMembro";
import { getClaims, sair } from "./auth";
import "./App.css";

// Deriva o "contexto da clínica" das claims do token (M3). Os componentes
// continuam recebendo `clinic` com `.id` (a API ignora — o clinicId vem do token).
function clinicDasClaims(claims) {
  return {
    id: claims["custom:clinicId"],
    role: claims["custom:role"] || "",
    email: claims.email || "",
    nome: claims.email || claims["custom:clinicId"],
  };
}

export default function App() {
  const [clinic, setClinic] = useState(null);
  const [aba, setAba] = useState("pacientes");
  const [mostrarMembro, setMostrarMembro] = useState(false);

  // Restaura a sessão do token guardado (não relogar a cada refresh).
  useEffect(() => {
    const claims = getClaims();
    if (claims && claims["custom:clinicId"]) setClinic(clinicDasClaims(claims));
  }, []);

  function aoLogar(claims) {
    setClinic(clinicDasClaims(claims));
  }
  function sairApp() {
    sair();
    setClinic(null);
  }

  if (!clinic) return <Login onLogin={aoLogar} />;

  const isAdmin = clinic.role === "admin";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-dot" />
          Clínica de Pilates
        </div>
        <div className="topbar-right">
          {isAdmin && (
            <button className="btn ghost" onClick={() => setMostrarMembro(true)}>
              + Membro
            </button>
          )}
          <span className="clinic-tag" title="Clínica vinculada ao seu usuário">
            {clinic.id}
            {clinic.role ? ` · ${clinic.role}` : ""}
          </span>
          <span className="user-email muted">{clinic.email}</span>
          <button className="btn ghost" onClick={sairApp}>
            Sair
          </button>
        </div>
      </header>

      <nav className="tabs">
        <button className={aba === "pacientes" ? "tab on" : "tab"} onClick={() => setAba("pacientes")}>
          Pacientes
        </button>
        <button className={aba === "aparelhos" ? "tab on" : "tab"} onClick={() => setAba("aparelhos")}>
          Aparelhos
        </button>
        <button className={aba === "pilates" ? "tab on" : "tab"} onClick={() => setAba("pilates")}>
          Pilates
        </button>
      </nav>

      <main className="content">
        {aba === "pacientes" && <Pacientes clinic={clinic} />}
        {aba === "aparelhos" && <Aparelhos clinic={clinic} />}
        {aba === "pilates" && <Pilates clinic={clinic} />}
      </main>

      {mostrarMembro && <AdicionarMembro onFechar={() => setMostrarMembro(false)} />}
    </div>
  );
}
