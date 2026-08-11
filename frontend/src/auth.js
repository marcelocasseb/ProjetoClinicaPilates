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

// `refreshAtual` é o fallback do refreshToken: na renovação (REFRESH_TOKEN_AUTH)
// o Cognito NÃO devolve um refreshToken novo — precisamos preservar o que já temos,
// senão a 1ª renovação apagaria o refresh e a sessão voltaria a durar só 1 hora.
function guardarSessao(result, refreshAtual = null) {
  const claims = decodeClaims(result.IdToken);
  localStorage.setItem(
    STORE_KEY,
    JSON.stringify({
      idToken: result.IdToken,
      accessToken: result.AccessToken,
      refreshToken: result.RefreshToken || refreshAtual,
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

// Renova o idToken com o refreshToken guardado (fluxo REFRESH_TOKEN_AUTH, já
// habilitado no App Client). O idToken do Cognito vale 1 hora — sem esta renovação
// o usuário era expulso a cada hora exata de uso, perdendo o que estava digitando.
// O refreshToken vale 30 dias, então na prática a sessão deixa de cair no expediente.
// Retorna as claims novas, ou `null` se não deu (refresh vencido/revogado).
export async function renovarSessao() {
  const s = getSessao();
  if (!s || !s.refreshToken) return null;
  try {
    const data = await cognito("InitiateAuth", {
      AuthFlow: "REFRESH_TOKEN_AUTH",
      ClientId: COGNITO_CLIENT_ID,
      AuthParameters: { REFRESH_TOKEN: s.refreshToken },
    });
    const result = data.AuthenticationResult;
    if (!result || !result.IdToken) return null;
    return guardarSessao(result, s.refreshToken);
  } catch {
    return null;
  }
}

// Quantos milissegundos faltam para o idToken vencer (`exp` é em segundos).
// `0` se não há sessão ou o token não traz `exp`.
export function msAteExpirar() {
  const claims = getClaims();
  if (!claims || !claims.exp) return 0;
  return claims.exp * 1000 - Date.now();
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
