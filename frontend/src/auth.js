// Autenticação via Cognito (M3 / AUTH-05), sem biblioteca: chamadas fetch diretas
// à API do Cognito Identity Provider usando o fluxo USER_PASSWORD_AUTH. O idToken
// (que carrega custom:clinicId e custom:role) é guardado no localStorage e enviado
// como Authorization: Bearer nas chamadas da API (ver api.js).
import { COGNITO_CLIENT_ID, COGNITO_REGION } from "./config";

const ENDPOINT = `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/`;
const STORE_KEY = "auth";

async function cognito(target, body) {
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || "Erro de autenticação");
    err.code = (data.__type || "").split("#").pop(); // ex.: "NotAuthorizedException"
    throw err;
  }
  return data;
}

// Decodifica o payload do JWT (idToken) — só para ler as claims no front.
export function decodeClaims(idToken) {
  try {
    const b64 = idToken.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(decodeURIComponent(escape(atob(b64))));
  } catch {
    return {};
  }
}

function guardarSessao(result) {
  const claims = decodeClaims(result.IdToken);
  localStorage.setItem(
    STORE_KEY,
    JSON.stringify({
      idToken: result.IdToken,
      accessToken: result.AccessToken,
      refreshToken: result.RefreshToken,
      claims,
    })
  );
  return claims;
}

// Login. Retorna { ok, claims } ou { challenge: "NEW_PASSWORD_REQUIRED", session, email }.
export async function login(email, senha) {
  const data = await cognito("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: COGNITO_CLIENT_ID,
    AuthParameters: { USERNAME: email, PASSWORD: senha },
  });
  if (data.ChallengeName === "NEW_PASSWORD_REQUIRED") {
    return { challenge: "NEW_PASSWORD_REQUIRED", session: data.Session, email };
  }
  return { ok: true, claims: guardarSessao(data.AuthenticationResult) };
}

// Conclui o desafio de 1º acesso (define a senha definitiva).
export async function definirNovaSenha(email, session, novaSenha) {
  const data = await cognito("RespondToAuthChallenge", {
    ChallengeName: "NEW_PASSWORD_REQUIRED",
    ClientId: COGNITO_CLIENT_ID,
    Session: session,
    ChallengeResponses: { USERNAME: email, NEW_PASSWORD: novaSenha },
  });
  return { ok: true, claims: guardarSessao(data.AuthenticationResult) };
}

export function getSessao() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY));
  } catch {
    return null;
  }
}

export function getIdToken() {
  const s = getSessao();
  return s ? s.idToken : null;
}

export function getClaims() {
  const s = getSessao();
  return s ? s.claims : null;
}

export function sair() {
  localStorage.removeItem(STORE_KEY);
}
