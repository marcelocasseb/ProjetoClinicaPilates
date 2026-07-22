import { useEffect, useState } from "react";
import Login from "./components/Login";
import Pacientes from "./components/Pacientes";
import Aparelhos from "./components/Aparelhos";
import "./App.css";

export default function App() {
  const [clinic, setClinic] = useState(null);
  const [aba, setAba] = useState("pacientes");

  // Persiste a clínica escolhida (demo) para não relogar a cada refresh.
  useEffect(() => {
    const salvo = localStorage.getItem("clinic");
    if (salvo) setClinic(JSON.parse(salvo));
  }, []);

  function entrar(c) {
    setClinic(c);
    localStorage.setItem("clinic", JSON.stringify(c));
  }
  function sair() {
    setClinic(null);
    localStorage.removeItem("clinic");
  }

  if (!clinic) return <Login onSelect={entrar} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-dot" />
          Clínica de Pilates
        </div>
        <div className="topbar-right">
          <span className="clinic-tag">{clinic.nome}</span>
          <button className="btn ghost" onClick={sair}>Trocar clínica</button>
        </div>
      </header>

      <nav className="tabs">
        <button className={aba === "pacientes" ? "tab on" : "tab"} onClick={() => setAba("pacientes")}>
          Pacientes
        </button>
        <button className={aba === "aparelhos" ? "tab on" : "tab"} onClick={() => setAba("aparelhos")}>
          Aparelhos
        </button>
      </nav>

      <main className="content">
        {aba === "pacientes" ? <Pacientes clinic={clinic} /> : <Aparelhos clinic={clinic} />}
      </main>
    </div>
  );
}
