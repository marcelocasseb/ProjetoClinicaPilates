// Cliente da API da Clínica de Pilates.
// Toda chamada envia o idToken do login como Authorization: Bearer (M3/AUTH-05).
// O clinicId agora vem do token (claim), não mais de header — o 3º parâmetro
// (clinic) é mantido por compatibilidade de assinatura, mas é ignorado.
import { API_URL } from "./config";
import { getIdToken, sair } from "./auth";

async function request(method, path, _clinic, body) {
  const token = getIdToken();
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  // Token ausente/expirado → limpa a sessão e volta ao login.
  if (res.status === 401) {
    sair();
    window.location.reload();
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const msg = (data && data.detail) || `Erro ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// --- Pacientes ---
export const pacientesApi = {
  list: (clinic) => request("GET", "/pacientes", clinic),
  create: (clinic, data) => request("POST", "/pacientes", clinic, data),
  update: (clinic, id, data) => request("PUT", `/pacientes/${id}`, clinic, data),
  remove: (clinic, id) => request("DELETE", `/pacientes/${id}`, clinic),
};

// --- Aparelhos ---
export const aparelhosApi = {
  list: (clinic) => request("GET", "/aparelhos", clinic),
  create: (clinic, data) => request("POST", "/aparelhos", clinic, data),
  update: (clinic, id, data) => request("PUT", `/aparelhos/${id}`, clinic, data),
  remove: (clinic, id) => request("DELETE", `/aparelhos/${id}`, clinic),
};

// --- Avaliações (por paciente, aninhadas — AVL-01..08) ---
export const avaliacoesApi = {
  list: (clinic, pacienteId) => request("GET", `/pacientes/${pacienteId}/avaliacoes`, clinic),
  create: (clinic, pacienteId, data) =>
    request("POST", `/pacientes/${pacienteId}/avaliacoes`, clinic, data),
  update: (clinic, pacienteId, id, data) =>
    request("PUT", `/pacientes/${pacienteId}/avaliacoes/${id}`, clinic, data),
  remove: (clinic, pacienteId, id) =>
    request("DELETE", `/pacientes/${pacienteId}/avaliacoes/${id}`, clinic),
};

// --- Sessões / Aulas (por paciente, aninhadas — SES-01..08) ---
export const sessoesApi = {
  list: (clinic, pacienteId) => request("GET", `/pacientes/${pacienteId}/sessoes`, clinic),
  create: (clinic, pacienteId, data) =>
    request("POST", `/pacientes/${pacienteId}/sessoes`, clinic, data),
  update: (clinic, pacienteId, id, data) =>
    request("PUT", `/pacientes/${pacienteId}/sessoes/${id}`, clinic, data),
  remove: (clinic, pacienteId, id) =>
    request("DELETE", `/pacientes/${pacienteId}/sessoes/${id}`, clinic),
};

// --- Membros da equipe (admin adiciona; herda a clínica do token — AUTH-07) ---
export const membrosApi = {
  create: (data) => request("POST", "/membros", null, data),
};

// --- Clínica do usuário logado (nome de exibição) ---
export const clinicaApi = {
  get: () => request("GET", "/clinica", null),
};

// --- ViaCEP (consulta de endereço pelo CEP, feita no front — AD-009) ---
export async function buscarCep(cep) {
  const digits = (cep || "").replace(/\D/g, "");
  if (digits.length !== 8) return null;
  try {
    const res = await fetch(`https://viacep.com.br/ws/${digits}/json/`);
    const data = await res.json();
    if (data.erro) return null;
    return {
      cep: digits,
      logradouro: data.logradouro || "",
      bairro: data.bairro || "",
      cidade: data.localidade || "",
      uf: data.uf || "",
    };
  } catch {
    return null;
  }
}
