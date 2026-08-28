import { useEffect, useState } from "react";
import Login from "./components/Login";
import Pacientes from "./components/Pacientes";
import Aparelhos from "./components/Aparelhos";
import Pilates from "./components/Pilates";
import Escala from "./components/Escala";
import AdicionarMembro from "./components/AdicionarMembro";
import SessaoExpirada from "./components/SessaoExpirada";
import { getClaims, sair } from "./auth";
import { clinicaApi, sessaoDescartada, sessaoRestaurada } from "./api";
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
  const [sessaoCaiu, setSessaoCaiu] = useState(false); // modal de re-login por cima da tela

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

  // api.js avisa quando o refresh token também não resolveu e só o usuário pode
  // destravar. Abrimos o modal SEM desmontar a árvore — o formulário em edição
  // continua na tela, atrás dele.
  useEffect(() => {
    const abrir = () => setSessaoCaiu(true);
    window.addEventListener("sessao-expirada", abrir);
    return () => window.removeEventListener("sessao-expirada", abrir);
  }, []);

  function aoLogar(claims) {
    setClinic(clinicDasClaims(claims));
  }

  // Re-login pelo modal: atualiza as claims e libera as requisições que ficaram
  // penduradas — o "Salvar" que o usuário clicou conclui sozinho.
  function aoReentrar(claims) {
    setClinic(clinicDasClaims(claims));
    setSessaoCaiu(false);
    sessaoRestaurada();
  }

  function sairApp() {
    if (sessaoCaiu) {
      setSessaoCaiu(false);
      sessaoDescartada();
    }
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
        <button className={aba === "escala" ? "tab on" : "tab"} onClick={() => setAba("escala")}>
          Escala
        </button>
      </nav>

      <main className="content">
        {aba === "pacientes" && <Pacientes clinic={clinic} />}
        {aba === "aparelhos" && <Aparelhos clinic={clinic} />}
        {aba === "pilates" && <Pilates clinic={clinic} />}
        {aba === "escala" && <Escala clinic={clinic} />}
      </main>

      {mostrarMembro && <AdicionarMembro onFechar={() => setMostrarMembro(false)} />}
      {sessaoCaiu && <SessaoExpirada onEntrar={aoReentrar} onSair={sairApp} />}
    </div>
  );
}
