import { useEffect, useRef, useState } from "react";
import Login from "./components/Login";
import Inicio from "./components/Inicio";
import Pacientes from "./components/Pacientes";
import Agenda from "./components/Agenda";
import Aparelhos from "./components/Aparelhos";
import Profissionais from "./components/Profissionais";
import Pilates from "./components/Pilates";
import Escala from "./components/Escala";
import Financeiro from "./components/Financeiro";
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

// Telas agrupadas em abas com lista suspensa.
const ABAS_PILATES = [
  { id: "pilates", rotulo: "Pilates" },
  { id: "escala", rotulo: "Escala" },
];
const ABAS_PARAMETRIZACAO = [
  { id: "profissionais", rotulo: "Profissionais" },
  { id: "aparelhos", rotulo: "Aparelhos" },
];

// Aba que abre uma lista suspensa com as telas do grupo. Fica destacada quando a
// tela aberta é de dentro dela; fecha ao escolher, clicar fora ou apertar Esc.
function MenuSuspenso({ rotulo, abas, aba, onEscolher }) {
  const [aberto, setAberto] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!aberto) return;
    const fora = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setAberto(false);
    };
    const esc = (e) => e.key === "Escape" && setAberto(false);
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [aberto]);

  return (
    <div className="tab-menu" ref={ref}>
      <button
        className={abas.some((a) => a.id === aba) ? "tab on" : "tab"}
        aria-haspopup="menu"
        aria-expanded={aberto}
        onClick={() => setAberto((v) => !v)}
      >
        {rotulo} <span className="tab-seta">▾</span>
      </button>
      {aberto && (
        <div className="tab-dropdown" role="menu">
          {abas.map((a) => (
            <button
              key={a.id}
              role="menuitem"
              className={aba === a.id ? "tab-opcao on" : "tab-opcao"}
              onClick={() => {
                onEscolher(a.id);
                setAberto(false);
              }}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [clinic, setClinic] = useState(null);
  const [clinicNome, setClinicNome] = useState(null); // nome de exibição (do backend)
  const [aba, setAba] = useState("inicio");
  const [secaoFin, setSecaoFin] = useState("caixa"); // sub-aba ao chegar pelo Início
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
    setAba("inicio");
  }

  // Atalhos da tela inicial. "financeiro" vindo do Início abre direto nas
  // mensalidades (é o que os cards de vencimento mostram).
  function navegar(destino) {
    if (destino === "financeiro") setSecaoFin("mensalidades");
    setAba(destino);
  }

  function abrirAba(destino) {
    if (destino === "financeiro") setSecaoFin("caixa");
    setAba(destino);
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
        <button className={aba === "inicio" ? "tab on" : "tab"} onClick={() => abrirAba("inicio")}>
          Início
        </button>
        <button className={aba === "pacientes" ? "tab on" : "tab"} onClick={() => setAba("pacientes")}>
          Pacientes
        </button>
        <button className={aba === "agenda" ? "tab on" : "tab"} onClick={() => setAba("agenda")}>
          Agenda
        </button>
        <MenuSuspenso rotulo="Pilates" abas={ABAS_PILATES} aba={aba} onEscolher={setAba} />
        {/* Financeiro é só de admin (FIN-06). Esconder a aba é higiene de UI — quem
            garante mesmo é o backend, que devolve 403 para quem não é admin. */}
        {isAdmin && (
          <button
            className={aba === "financeiro" ? "tab on" : "tab"}
            onClick={() => abrirAba("financeiro")}
          >
            Financeiro
          </button>
        )}
        <MenuSuspenso
          rotulo="Parametrização"
          abas={ABAS_PARAMETRIZACAO}
          aba={aba}
          onEscolher={setAba}
        />
      </nav>

      <main className="content">
        {aba === "inicio" && <Inicio clinic={clinic} onNavegar={navegar} />}
        {aba === "pacientes" && <Pacientes clinic={clinic} />}
        {aba === "agenda" && <Agenda clinic={clinic} clinicaNome={clinicNome} onNavegar={setAba} />}
        {aba === "profissionais" && <Profissionais clinic={clinic} />}
        {aba === "aparelhos" && <Aparelhos clinic={clinic} />}
        {aba === "pilates" && <Pilates clinic={clinic} onNavegar={setAba} />}
        {aba === "escala" && <Escala clinic={clinic} />}
        {aba === "financeiro" && isAdmin && <Financeiro key={secaoFin} clinic={clinic} secaoInicial={secaoFin} />}
      </main>

      {mostrarMembro && <AdicionarMembro onFechar={() => setMostrarMembro(false)} />}
      {sessaoCaiu && <SessaoExpirada onEntrar={aoReentrar} onSair={sairApp} />}
    </div>
  );
}
