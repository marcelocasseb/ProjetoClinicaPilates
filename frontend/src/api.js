// Cliente da API da Clínica de Pilates.
// Toda chamada envia o header X-Clinic-Id (multi-tenant, AD-007). No M3 isso
// será substituído pelo token do login — mudando só este arquivo.
import { API_URL } from "./config";

async function request(method, path, clinicId, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Clinic-Id": clinicId,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

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
