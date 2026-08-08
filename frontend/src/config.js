// Configuração do front.
// API e Cognito vêm de variáveis VITE_* (.env / ambiente de build); os defaults
// apontam para a stack já deployada (clinica-pilates, us-east-1).
export const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://8f1ffym997.execute-api.us-east-1.amazonaws.com";

// Cognito (M3 / AUTH-05). Preencher VITE_COGNITO_CLIENT_ID com o output
// `UserPoolClientId` da stack ao publicar. Sem ele, o login não funciona.
export const COGNITO_REGION = import.meta.env.VITE_COGNITO_REGION || "us-east-1";
export const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || "";
