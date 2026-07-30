import { useEffect, useState } from "react";
import Login from "./components/Login";
import Pacientes from "./components/Pacientes";
import Aparelhos from "./components/Aparelhos";
import Pilates from "./components/Pilates";
import AdicionarMembro from "./components/AdicionarMembro";
import { getClaims, sair } from "./auth";
import { clinicaApi } from "./api";
import iconUrl from "./assets/pilatesone-icon.jpg";
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
  const [clinicNome, setClinicNome] = useState(null); // nome de exibição (do backend)
  const [aba, setAba] = useState("pacientes");
  const [mostrarMembro, setMostrarMembro] = useState(false);

  // Restaura a sessão do token guardado (não relogar a cada refresh).
  useEffect(() => {
    const claims = getClaims();
    if (claims && claims["custom:clinicId"]) setClinic(clinicDasClaims(claims));
  }, []);

  // Busca o nome de exibição da clínica (mostrado no topo em vez do clinicId).
  useEffect(() => {
    if (!clinic) return;
    let ativo = true;
    clinicaApi
      .get()
      .then((r) => ativo && setClinicNome(r?.nome || null))
      .catch(() => {});
    return () => {
      ativo = false;
    };
  }, [clinic]);

  function aoLogar(claims) {
    setClinic(clinicDasClaims(claims));
  }
  function sairApp() {
    sair();
    setClinic(null);
    setClinicNome(null);
  }

  if (!clinic) return <Login onLogin={aoLogar} />;

  const isAdmin = clinic.role === "admin";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src={iconUrl} alt="" className="brand-logo" />
          <span className="brand-name">Pilates One</span>
        </div>
        <div className="topbar-right">
          {isAdmin && (
            <button className="btn ghost" onClick={() => setMostrarMembro(true)}>
              + Membro
            </button>
          )}
          <span className="clinic-tag" title={clinicNome || clinic.id}>
            <span className="clinic-nome">{clinicNome || clinic.id}</span>
            {clinic.role ? <span className="clinic-role">{clinic.role}</span> : null}
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
