import { useEffect, useMemo, useRef, useState } from "react";
import { agendaApi, pacientesApi, profissionaisApi } from "../api";
import {
  FORMAS_PAGAMENTO,
  brParaCentavos,
  centavosParaBR,
  formatDataBR,
  hojeISO,
  labelForma,
  maskMoeda,
  maskTelefone,
} from "../utils/format";
import { DIAS, HORARIOS } from "./Escala";

// Agenda: quem vem em cada DATA (independente da Escala, que é a grade fixa da
// semana). Mostra uma semana por vez: faixa com os 7 dias e, embaixo, os horários
// do dia escolhido. Quem não tem cadastro entra só com nome/telefone ("novo") e
// pode virar paciente depois, sem perder a marcação.

const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

// "YYYY-MM-DD" <-> Date no fuso LOCAL (toISOString viraria o dia 3h antes no Brasil).
const paraDate = (iso) => {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d);
};
const paraISO = (dt) => dt.toLocaleDateString("en-CA");
const somaDias = (iso, n) => {
  const dt = paraDate(iso);
  dt.setDate(dt.getDate() + n);
  return paraISO(dt);
};
// Segunda-feira da semana da data (a semana da clínica começa na segunda).
const segundaDe = (iso) => somaDias(iso, -((paraDate(iso).getDay() + 6) % 7));

const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;
const SWIPE_MIN = 60;

function tituloSemana(ini) {
  const a = paraDate(ini);
  const b = paraDate(somaDias(ini, 6));
  if (a.getMonth() === b.getMonth()) return `${a.getDate()} a ${b.getDate()} de ${MESES[b.getMonth()]}`;
  return `${a.getDate()} de ${MESES[a.getMonth()]} a ${b.getDate()} de ${MESES[b.getMonth()]}`;
}

// --- Lembrete por WhatsApp -------------------------------------------------
// O link wa.me abre o WhatsApp (app no celular; Desktop ou Web no computador) com a
// mensagem pronta para o número; quem envia é o WhatsApp logado ali — de preferência
// o da clínica. Nada passa pelo nosso servidor.

// "(91) 98111-1111" -> "5591981111111". Sem DDD+número (10/11 dígitos) não há link.
function numeroWhats(telefone) {
  const d = (telefone || "").replace(/\D/g, "");
  if (d.length === 10 || d.length === 11) return `55${d}`;
  if ((d.length === 12 || d.length === 13) && d.startsWith("55")) return d;
  return null;
}

// "06:00" -> "6h00"; "18:30" -> "18h30".
const horaFalada = (hhmm) => `${Number(hhmm.slice(0, 2))}h${hhmm.slice(3)}`;

// "hoje", "amanhã" ou "na quarta, 22/10" / "no sábado, 25/10".
function quandoFalado(data, hoje) {
  if (data === hoje) return "hoje";
  if (data === somaDias(hoje, 1)) return "amanhã";
  const dt = paraDate(data);
  const nome = DIAS[(dt.getDay() + 6) % 7].nome.toLowerCase();
  const artigo = nome === "sábado" || nome === "domingo" ? "no" : "na";
  const dd = String(dt.getDate()).padStart(2, "0");
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  return `${artigo} ${nome}, ${dd}/${mm}`;
}

// "Olá, Nayara! Somos da Clínica Zen. Podemos confirmar sua presença amanhã às
// 10h00 com o profissional Dr. Paulo?" — clínica e profissional entram só se houver.
function linkWhats(a, hoje, clinica) {
  const numero = numeroWhats(a.telefone);
  if (!numero) return null;
  const nome = (a.nome || "").trim().split(/\s+/)[0];
  const primeiro = nome.charAt(0).toUpperCase() + nome.slice(1);
  const texto =
    `Olá, ${primeiro}!` +
    (clinica ? ` Somos da ${clinica}.` : "") +
    ` Podemos confirmar sua presença ${quandoFalado(a.data, hoje)} às ${horaFalada(a.hora)}` +
    (a.profissional ? ` com o profissional ${a.profissional}` : "") +
    "?";
  return `https://wa.me/${numero}?text=${encodeURIComponent(texto)}`;
}

const IconeWhats = (
  <svg viewBox="0 0 24 24" aria-hidden="true" width="15" height="15" fill="currentColor">
    <path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.8 11.9 11.9 0 0 0 4.6 4c1.7.7 2.4.8 3.2.7.5-.1 1.5-.6 1.8-1.2.2-.6.2-1.1.1-1.2l-.4-.3z" />
  </svg>
);

export default function Agenda({ clinic, clinicaNome, onNavegar }) {
  const hoje = hojeISO();
  const [dia, setDia] = useState(hoje);
  const semana = segundaDe(dia);
  const datas = useMemo(() => DIAS.map((_, i) => somaDias(semana, i)), [semana]);

  const [itens, setItens] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const [novoEm, setNovoEm] = useState(null); // hora do modal "marcar"
  const [modo, setModo] = useState("cadastrado"); // "cadastrado" | "novo"
  const [escolhido, setEscolhido] = useState("");
  const [nomeNovo, setNomeNovo] = useState("");
  const [telNovo, setTelNovo] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [detalhe, setDetalhe] = useState(null); // pessoa nova aberta (cadastrar)
  const toqueX = useRef(null);

  // Pagamento do agendamento: "Receber" lança a entrada no Caixa; "Pago" mostra e
  // desfaz. Sem preço de tabela — a Agenda não é do Pilates, o valor é digitado.
  const [receber, setReceber] = useState(null); // item do modal "Receber"
  const [valorTxt, setValorTxt] = useState("");
  const [forma, setForma] = useState("");
  const [verPago, setVerPago] = useState(null); // item do modal "Pago"

  // Profissionais: escolhido na marcação (opcional) e trocado depois pela linha. O
  // cadastro fica em Parametrização → Profissionais.
  const [profissionais, setProfissionais] = useState([]);
  const [profEscolhido, setProfEscolhido] = useState("");
  const [trocarProf, setTrocarProf] = useState(null); // item do modal "Profissional"

  // Pacientes e profissionais uma vez; a semana a cada troca de semana.
  useEffect(() => {
    pacientesApi.list(clinic.id).then(setPacientes).catch(() => {});
    profissionaisApi.list(clinic.id).then(setProfissionais).catch(() => {});
  }, [clinic.id]);

  async function carregar() {
    setErro("");
    setCarregando(true);
    try {
      setItens(await agendaApi.list(clinic.id, semana, somaDias(semana, 6)));
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, [clinic.id, semana]);

  const porData = useMemo(() => {
    const mapa = {};
    for (const a of itens) (mapa[a.data] ||= []).push(a);
    return mapa;
  }, [itens]);

  const doDia = porData[dia] || [];
  const porHora = useMemo(() => {
    const mapa = new Map();
    for (const a of doDia) {
      if (!mapa.has(a.hora)) mapa.set(a.hora, []);
      mapa.get(a.hora).push(a);
    }
    return mapa;
  }, [doDia]);
  const linhas = useMemo(
    () => [...new Set([...HORARIOS, ...porHora.keys()])].sort(),
    [porHora]
  );

  const alunosOrdenados = useMemo(
    () => [...pacientes].sort((a, b) => (a.nome || "").localeCompare(b.nome || "", "pt-BR")),
    [pacientes]
  );
  const disponiveis = useMemo(() => {
    if (!novoEm) return [];
    const ja = new Set((porHora.get(novoEm) || []).map((a) => a.pacienteId).filter(Boolean));
    return alunosOrdenados.filter((p) => !ja.has(p.id));
  }, [novoEm, porHora, alunosOrdenados]);

  const dt = paraDate(dia);
  const nomeDia = DIAS[(dt.getDay() + 6) % 7].nome;

  function abrirMarcar(hora) {
    setErro("");
    setEscolhido("");
    setNomeNovo("");
    setTelNovo("");
    setProfEscolhido("");
    setModo(pacientes.length ? "cadastrado" : "novo");
    setNovoEm(hora);
  }

  // Aviso (não bloqueio) quando o profissional já tem alguém no horário: pode ser
  // atendimento em grupo, ou pode ser engano — quem decide é a recepção.
  function confirmaConflito(profissionalId, hora, ignorarId) {
    if (!profissionalId) return true;
    const outros = (porHora.get(hora) || []).filter(
      (x) => x.profissionalId === profissionalId && x.id !== ignorarId
    );
    if (!outros.length) return true;
    const prof = profissionais.find((p) => p.id === profissionalId)?.nome || "Este profissional";
    return confirm(
      `${prof} já tem ${outros.map((x) => x.nome).join(", ")} às ${hora}. Marcar mesmo assim?`
    );
  }

  async function marcar() {
    if (!confirmaConflito(profEscolhido, novoEm)) return;
    const base = { data: dia, hora: novoEm, profissionalId: profEscolhido };
    const corpo =
      modo === "cadastrado"
        ? { ...base, pacienteId: escolhido }
        : { ...base, nome: nomeNovo, telefone: telNovo };
    setSalvando(true);
    setErro("");
    try {
      const novo = await agendaApi.agendar(clinic.id, corpo);
      setItens((atual) => [...atual, novo]);
      setNovoEm(null);
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  const trocar = (novo) => setItens((atual) => atual.map((x) => (x.id === novo.id ? novo : x)));

  async function salvarProfissionalDaMarcacao(profissionalId) {
    if (!confirmaConflito(profissionalId, trocarProf.hora, trocarProf.id)) return;
    setSalvando(true);
    setErro("");
    try {
      trocar(await agendaApi.definirProfissional(clinic.id, trocarProf, profissionalId || null));
      setTrocarProf(null);
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  // Atalho para o cadastro quando ainda não há profissionais.
  const linkCadastroProf = (
    <button type="button" className="link" onClick={() => onNavegar?.("profissionais")}>
      Parametrização → Profissionais
    </button>
  );

  function abrirReceber(a) {
    setErro("");
    setValorTxt("");
    setForma("");
    setReceber(a);
  }

  async function confirmarReceber() {
    setSalvando(true);
    setErro("");
    try {
      trocar(
        await agendaApi.receber(clinic.id, receber, {
          valorCentavos: brParaCentavos(valorTxt),
          formaPagamento: forma,
          dataPagamento: hojeISO(),
        })
      );
      setReceber(null);
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  async function desfazerPagamento(a) {
    if (!confirm(`Desfazer o pagamento de ${a.nome}? A entrada de R$ ${centavosParaBR(a.pagamento.valorCentavos)} sai do Caixa.`)) return;
    setSalvando(true);
    setErro("");
    try {
      trocar(await agendaApi.desfazerPagamento(clinic.id, a));
      setVerPago(null);
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  async function desmarcar(a) {
    const pergunta = a.pagamento
      ? `${a.nome} já pagou R$ ${centavosParaBR(a.pagamento.valorCentavos)} por este agendamento. ` +
        "Desmarcar também tira essa entrada do Caixa. Continuar?"
      : `Desmarcar ${a.nome} de ${nomeDia.toLowerCase()}, ${a.hora}?`;
    if (!confirm(pergunta)) return;
    setErro("");
    try {
      if (a.pagamento) await agendaApi.desfazerPagamento(clinic.id, a);
      await agendaApi.remover(clinic.id, a);
      setItens((atual) => atual.filter((x) => x.id !== a.id));
    } catch (e) {
      setErro(e.message);
      carregar();
    }
  }

  // Pessoa nova -> paciente: cria o cadastro com nome/telefone e liga a marcação.
  // O resto do cadastro (CPF, endereço…) se completa depois na aba Pacientes.
  async function cadastrar(a) {
    setSalvando(true);
    setErro("");
    try {
      const p = await pacientesApi.create(clinic.id, { nome: a.nome, telefone: a.telefone || "" });
      const ligado = await agendaApi.vincular(clinic.id, a, p.id);
      setPacientes((atual) => [...atual, p]);
      setItens((atual) => atual.map((x) => (x.id === a.id ? ligado : x)));
      setDetalhe(null);
    } catch (e) {
      setErro(e.message);
    } finally {
      setSalvando(false);
    }
  }

  function fimToque(e) {
    if (toqueX.current == null) return;
    const dx = e.changedTouches[0].clientX - toqueX.current;
    toqueX.current = null;
    if (Math.abs(dx) >= SWIPE_MIN) setDia((d) => somaDias(d, dx < 0 ? 1 : -1));
  }

  const podeMarcar =
    modo === "cadastrado" ? Boolean(escolhido) : nomeNovo.trim().length > 0;

  return (
    <div>
      {erro && <div className="erro">{erro}</div>}

      <div className="card">
        <div className="agenda-topo">
          <button type="button" className="btn ghost agenda-nav" aria-label="Semana anterior"
            onClick={() => setDia(somaDias(dia, -7))}>‹</button>
          <h2>{tituloSemana(semana)}</h2>
          <button type="button" className="btn ghost agenda-nav" aria-label="Próxima semana"
            onClick={() => setDia(somaDias(dia, 7))}>›</button>
          {dia !== hoje ? (
            <button type="button" className="btn agenda-hoje-btn" onClick={() => setDia(hoje)}>
              Hoje
            </button>
          ) : null}
        </div>

        <div className="escala-dias" role="tablist">
          {datas.map((d, i) => (
            <button
              key={d}
              type="button"
              role="tab"
              aria-selected={d === dia}
              className={"escala-dia" + (d === dia ? " on" : "") + (d === hoje ? " hoje" : "")}
              onClick={() => setDia(d)}
            >
              <span className="escala-dia-curto">{DIAS[i].curto}</span>
              <span className="escala-dia-conta">{paraDate(d).getDate()}</span>
              <span className="agenda-dia-qtd">
                {(porData[d] || []).length ? (porData[d] || []).length : "·"}
              </span>
            </button>
          ))}
        </div>

        <div className="escala-dia-titulo">
          <strong>
            {nomeDia}, {dt.getDate()} de {MESES[dt.getMonth()]}
          </strong>
          {dia === hoje && <span className="escala-hoje">hoje</span>}
          <span className="muted">{plural(doDia.length, "marcação", "marcações")}</span>
        </div>

        {carregando ? (
          <div className="loading">
            <span className="spinner" />
            Carregando a agenda…
          </div>
        ) : (
          <div
            key={dia}
            className="escala-horarios"
            onTouchStart={(e) => (toqueX.current = e.touches[0].clientX)}
            onTouchEnd={fimToque}
          >
            {linhas.map((hora) => {
              const lista = porHora.get(hora) || [];
              return (
                <div key={hora} className={lista.length ? "escala-slot cheio" : "escala-slot"}>
                  <div className="escala-slot-hora">{hora}</div>
                  <div className="escala-slot-alunos">
                    {lista.length ? (
                      lista.map((a) => (
                        <span key={a.id} className={a.novo ? "aluno-chip agenda-chip novo" : "aluno-chip agenda-chip"}>
                          <span className="agenda-pessoa">
                            {a.novo ? (
                              <button
                                type="button"
                                className="aluno-nome agenda-nome-btn"
                                title="Pessoa sem cadastro — toque para cadastrar"
                                onClick={() => {
                                  setErro("");
                                  setDetalhe(a);
                                }}
                              >
                                {a.nome}
                              </button>
                            ) : (
                              <span className="aluno-nome" title={a.nome}>{a.nome}</span>
                            )}
                            <button
                              type="button"
                              className={a.profissional ? "agenda-prof" : "agenda-prof vazio"}
                              title="Escolher ou trocar o profissional"
                              onClick={() => {
                                setErro("");
                                setTrocarProf(a);
                              }}
                            >
                              {a.profissional || "+ profissional"}
                            </button>
                          </span>
                          {a.novo && <span className="agenda-selo-novo">novo</span>}
                          {a.pagamento ? (
                            <button
                              type="button"
                              className="agenda-pago"
                              title={`Pago: R$ ${centavosParaBR(a.pagamento.valorCentavos)}`}
                              onClick={() => {
                                setErro("");
                                setVerPago(a);
                              }}
                            >
                              ✓ Pago
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="agenda-receber"
                              title="Receber pagamento deste agendamento"
                              aria-label={`Receber pagamento de ${a.nome}`}
                              onClick={() => abrirReceber(a)}
                            >
                              R$
                            </button>
                          )}
                          {linkWhats(a, hoje, clinicaNome) ? (
                            <a
                              className="agenda-whats"
                              href={linkWhats(a, hoje, clinicaNome)}
                              target="_blank"
                              rel="noopener noreferrer"
                              title={`Enviar lembrete no WhatsApp para ${a.nome}`}
                              aria-label={`Enviar lembrete no WhatsApp para ${a.nome}`}
                            >
                              {IconeWhats}
                            </a>
                          ) : (
                            <span
                              className="agenda-whats off"
                              title="Sem telefone válido (com DDD) para o WhatsApp"
                            >
                              {IconeWhats}
                            </span>
                          )}
                          <button
                            type="button"
                            className="aluno-x"
                            title={`Desmarcar ${a.nome}`}
                            onClick={() => desmarcar(a)}
                          >
                            ✕
                          </button>
                        </span>
                      ))
                    ) : (
                      <span className="muted">Livre</span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="escala-slot-add"
                    aria-label={`Marcar alguém — ${nomeDia}, ${hora}`}
                    onClick={() => abrirMarcar(hora)}
                  >
                    +
                  </button>
                </div>
              );
            })}
          </div>
        )}
        <p className="muted escala-dica-cel agenda-dica">
          Toque em <strong>+</strong> para marcar. Quem ainda não tem cadastro aparece como{" "}
          <span className="agenda-selo-novo">novo</span>; toque no nome para cadastrar. O ícone
          do WhatsApp abre a mensagem de confirmação pronta.
        </p>
      </div>

      {novoEm && (
        <div className="modal-overlay" onClick={() => setNovoEm(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>
              {nomeDia}, {dt.getDate()}/{String(dt.getMonth() + 1).padStart(2, "0")} às {novoEm}
            </h2>
            {erro && <div className="erro">{erro}</div>}

            <div className="agenda-modo" role="tablist">
              <button type="button" role="tab" aria-selected={modo === "cadastrado"}
                className={modo === "cadastrado" ? "on" : ""} onClick={() => setModo("cadastrado")}>
                Paciente cadastrado
              </button>
              <button type="button" role="tab" aria-selected={modo === "novo"}
                className={modo === "novo" ? "on" : ""} onClick={() => setModo("novo")}>
                Sem cadastro
              </button>
            </div>

            {modo === "cadastrado" ? (
              disponiveis.length === 0 ? (
                <p className="muted">
                  {pacientes.length === 0
                    ? "Nenhum paciente cadastrado ainda. Use “Sem cadastro”."
                    : "Todos os pacientes já estão marcados neste horário."}
                </p>
              ) : (
                <>
                  <label className="escala-label">Paciente</label>
                  <select className="escala-select" value={escolhido}
                    onChange={(e) => setEscolhido(e.target.value)}>
                    <option value="">— escolha um paciente —</option>
                    {disponiveis.map((p) => (
                      <option key={p.id} value={p.id}>{p.nome}</option>
                    ))}
                  </select>
                </>
              )
            ) : (
              <>
                <label className="escala-label">Nome</label>
                <input className="escala-select" value={nomeNovo} maxLength={120} autoFocus
                  placeholder="Ex.: João Silva"
                  onChange={(e) => setNomeNovo(e.target.value)} />
                <label className="escala-label">Telefone (opcional)</label>
                <input className="escala-select" value={telNovo} inputMode="tel"
                  placeholder="(00) 00000-0000"
                  onChange={(e) => setTelNovo(maskTelefone(e.target.value))} />
              </>
            )}

            <label className="escala-label">Profissional (opcional)</label>
            {profissionais.length ? (
              <select className="escala-select" value={profEscolhido}
                onChange={(e) => setProfEscolhido(e.target.value)}>
                <option value="">— sem profissional —</option>
                {profissionais.map((p) => (
                  <option key={p.id} value={p.id}>{p.nome}</option>
                ))}
              </select>
            ) : (
              <p className="muted agenda-sem-prof">
                Nenhum profissional cadastrado. Cadastre em {linkCadastroProf}.
              </p>
            )}

            <div className="modal-actions">
              <button type="button" className="btn" onClick={() => setNovoEm(null)}>
                Fechar
              </button>
              <button type="button" className="btn primary" disabled={!podeMarcar || salvando}
                onClick={marcar}>
                {salvando ? "Marcando…" : "Marcar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {detalhe && (
        <div className="modal-overlay" onClick={() => setDetalhe(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>{detalhe.nome}</h2>
            {erro && <div className="erro">{erro}</div>}
            <p className="muted">
              Ainda sem cadastro · {DIAS[(paraDate(detalhe.data).getDay() + 6) % 7].nome.toLowerCase()},{" "}
              {detalhe.hora}
            </p>
            {detalhe.telefone ? (
              <p>
                Telefone: <a href={`tel:${detalhe.telefone.replace(/\D/g, "")}`}>{detalhe.telefone}</a>
              </p>
            ) : null}
            <p className="muted">
              “Cadastrar como paciente” cria o cadastro com o nome e o telefone acima e liga esta
              marcação a ele. Os demais dados você completa na aba Pacientes.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn" onClick={() => setDetalhe(null)}>
                Fechar
              </button>
              <button type="button" className="btn primary" disabled={salvando}
                onClick={() => cadastrar(detalhe)}>
                {salvando ? "Cadastrando…" : "Cadastrar como paciente"}
              </button>
            </div>
          </div>
        </div>
      )}

      {receber && (
        <div className="modal-overlay" onClick={() => setReceber(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>Receber — {receber.nome}</h2>
            <p className="muted">
              Agendamento de {formatDataBR(receber.data).slice(0, 5)} às {receber.hora}. Vai como
              entrada no Caixa com a data de hoje.
            </p>
            {erro && <div className="erro">{erro}</div>}

            <label className="escala-label">Valor (R$)</label>
            <input className="escala-select" value={valorTxt} inputMode="numeric" autoFocus
              placeholder="0,00" onChange={(e) => setValorTxt(maskMoeda(e.target.value))} />
            <label className="escala-label">Forma de pagamento</label>
            <select className="escala-select" value={forma} onChange={(e) => setForma(e.target.value)}>
              {FORMAS_PAGAMENTO.map((f) => (
                <option key={f.v} value={f.v}>{f.label}</option>
              ))}
            </select>

            <div className="modal-actions">
              <button type="button" className="btn" onClick={() => setReceber(null)}>
                Fechar
              </button>
              <button type="button" className="btn primary"
                disabled={brParaCentavos(valorTxt) <= 0 || salvando} onClick={confirmarReceber}>
                {salvando ? "Registrando…" : "Confirmar pagamento"}
              </button>
            </div>
          </div>
        </div>
      )}

      {verPago && (
        <div className="modal-overlay" onClick={() => setVerPago(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>✓ Pago — {verPago.nome}</h2>
            {erro && <div className="erro">{erro}</div>}
            <p className="agenda-pago-valor">R$ {centavosParaBR(verPago.pagamento.valorCentavos)}</p>
            <p className="muted">
              {labelForma(verPago.pagamento.formaPagamento)} · recebido em{" "}
              {formatDataBR(verPago.pagamento.dataPagamento)}
            </p>
            <div className="modal-actions">
              <button type="button" className="btn danger-ghost" disabled={salvando}
                onClick={() => desfazerPagamento(verPago)}>
                {salvando ? "Desfazendo…" : "Desfazer pagamento"}
              </button>
              <button type="button" className="btn" onClick={() => setVerPago(null)}>
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {trocarProf && (
        <div className="modal-overlay" onClick={() => setTrocarProf(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2>Profissional — {trocarProf.nome}</h2>
            <p className="muted">
              {formatDataBR(trocarProf.data).slice(0, 5)} às {trocarProf.hora}
            </p>
            {erro && <div className="erro">{erro}</div>}
            {profissionais.length === 0 ? (
              <p className="muted">Nenhum profissional cadastrado. Cadastre em {linkCadastroProf}.</p>
            ) : (
              <div className="agenda-prof-lista">
                {profissionais.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={p.id === trocarProf.profissionalId ? "on" : ""}
                    disabled={salvando}
                    onClick={() => salvarProfissionalDaMarcacao(p.id)}
                  >
                    {p.nome}
                  </button>
                ))}
              </div>
            )}
            <div className="modal-actions">
              {trocarProf.profissionalId && (
                <button type="button" className="btn danger-ghost" disabled={salvando}
                  onClick={() => salvarProfissionalDaMarcacao(null)}>
                  Tirar profissional
                </button>
              )}
              <button type="button" className="btn" onClick={() => setTrocarProf(null)}>
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
