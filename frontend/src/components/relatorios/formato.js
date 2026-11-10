import { centavosParaBR, labelForma } from "../../utils/format";

// Formatação compartilhada pelos relatórios (os valores chegam em centavos inteiros).

export const reais = (c) => `R$ ${centavosParaBR(c ?? 0)}`;

// Eixo de gráfico: "R$ 0", "R$ 500", "R$ 1,5 mil", "R$ 20 mil".
export function reaisCurto(c) {
  const v = (c ?? 0) / 100;
  if (Math.abs(v) < 1000) return `R$ ${Math.round(v)}`;
  const mil = v / 1000;
  const txt = Number.isInteger(mil) ? String(mil) : mil.toFixed(1).replace(".", ",");
  return `R$ ${txt} mil`;
}

export const inteiro = (n) => (n ?? 0).toLocaleString("pt-BR");

// Forma de pagamento: as atuais pelo rótulo do Caixa; as duas especiais do relatório.
export function nomeForma(forma) {
  if (forma === "cartao") return "Cartão (antigo)";
  if (forma === "nao_informado") return "Não informado";
  return labelForma(forma);
}

// Timestamp ISO (UTC) → data no fuso do navegador, dd/mm/aaaa.
export const dataLocal = (iso) => (iso ? new Date(iso).toLocaleDateString("pt-BR") : "—");

// "AAAA-MM-DD" → "dd/mm".
export const diaMes = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}` : "");

const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const mesCurto = (mes) => MESES_CURTOS[Number(mes.slice(5, 7)) - 1];
export { formatMesBR as mesLongo } from "../../utils/format";

// "AAAA-MM-DD" → "dd/mm/aaaa".
export const dataBR = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "");

// O período não fecha em meses inteiros? (aí o gráfico mensal mostra mais que o período)
export function periodoParcial(de, ate) {
  if (!de || !ate) return false;
  const [a, m] = ate.split("-").map(Number);
  const ultimo = new Date(Date.UTC(a, m, 0)).getUTCDate();
  return de.slice(8) !== "01" || Number(ate.slice(8)) !== ultimo;
}

export const NOTA_MESES_INTEIROS =
  "O gráfico mostra os meses inteiros; os números acima contam só o período escolhido.";

export const plural = (n, um, varios) => `${inteiro(n)} ${n === 1 ? um : varios}`;

// Cores das séries (ordem fixa; validadas para daltonismo contra o fundo branco).
export const SERIE_1 = "var(--serie-1)";
export const SERIE_2 = "var(--serie-2)";
