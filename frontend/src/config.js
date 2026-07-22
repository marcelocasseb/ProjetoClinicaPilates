// Configuração do demo.
// A URL da API pode ser sobrescrita por VITE_API_URL (.env); por padrão aponta
// para a stack já deployada (clinica-pilates, us-east-1).
export const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://8f1ffym997.execute-api.us-east-1.amazonaws.com";

// Clínicas "chumbadas" para o demo (login simples). No M3 (Cognito) isso vira
// login de verdade e o clinicId passa a vir do token — não mais daqui.
export const CLINICS = [
  { id: "clinica-zen", nome: "Clínica Zen" },
  { id: "clinica-corpo", nome: "Corpo em Movimento" },
];
