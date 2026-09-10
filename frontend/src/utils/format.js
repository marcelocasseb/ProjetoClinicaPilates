// Máscaras e validações de formulário (front).

export const onlyDigits = (v) => (v || "").replace(/\D/g, "");

// 000.000.000-00
export function maskCpf(v) {
  const d = onlyDigits(v).slice(0, 11);
  if (d.length > 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
  if (d.length > 6) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  if (d.length > 3) return `${d.slice(0, 3)}.${d.slice(3)}`;
  return d;
}

// (00) 00000-0000  (celular) ou (00) 0000-0000 (fixo)
export function maskTelefone(v) {
  const d = onlyDigits(v).slice(0, 11);
  if (d.length === 0) return "";
  if (d.length <= 2) return `(${d}`;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

// 00000-000
export function maskCep(v) {
  const d = onlyDigits(v).slice(0, 8);
  if (d.length > 5) return `${d.slice(0, 5)}-${d.slice(5)}`;
  return d;
}

// Data de hoje em YYYY-MM-DD no fuso local (default do campo de data da avaliação).
export const hojeISO = () => new Date().toLocaleDateString("en-CA");

// YYYY-MM-DD -> DD/MM/YYYY (exibição).
export function formatDataBR(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  if (!y || !m || !d) return iso;
  return `${d}/${m}/${y}`;
}

// "Natalia de Sousa Santos" -> "Natalia Santos". Usado para pré-preencher o
// profissional responsável com o nome de quem está logado. Nome com uma palavra
// só volta inteiro; vazio/ausente volta "" (melhor campo em branco do que palpite).
export function primeiroEUltimoNome(completo) {
  const partes = (completo || "").trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "";
  if (partes.length === 1) return partes[0];
  return `${partes[0]} ${partes[partes.length - 1]}`;
}

// --- Dinheiro (feature fluxo-caixa, FIN-09) --------------------------------
// O valor trafega para a API como INTEIRO EM CENTAVOS e só vira texto na
// exibição — nenhum float encosta no dinheiro. Um `parseFloat("1.234,56")` em
// algum lugar do caminho é exatamente como um centavo some do saldo do mês.

// Digitação progressiva da direita para a esquerda: "1" -> "0,01",
// "150" -> "1,50", "123456" -> "1.234,56". Mesmo padrão de maskCpf/maskTelefone.
export function maskMoeda(v) {
  const d = onlyDigits(v).slice(0, 11); // teto de ~R$ 999 milhões, de sobra
  if (!d) return "";
  return centavosParaBR(parseInt(d, 10));
}

// 123456 -> "1.234,56". Aceita null/undefined para não quebrar tela vazia.
export function centavosParaBR(c) {
  const n = Number.isFinite(c) ? Math.trunc(c) : 0;
  const negativo = n < 0;
  const abs = String(Math.abs(n)).padStart(3, "0");
  const reais = abs.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${negativo ? "-" : ""}${reais},${abs.slice(-2)}`;
}

// "1.234,56" -> 123456. Vazio -> 0. É o inverso exato de centavosParaBR.
export function brParaCentavos(s) {
  const d = onlyDigits(s);
  return d ? parseInt(d, 10) : 0;
}

// Formas de pagamento. Esta lista espelha a que o backend valida
// (`FORMAS_PAGAMENTO` em schemas_financeiro.py) — mandar algo fora dela dá 400.
// Fica aqui, e não num componente, porque o Caixa e a baixa de mensalidade
// precisam das MESMAS opções: forma divergente entre as duas telas produziria
// extrato incoerente ("pix" numa, vazio na outra, pro mesmo tipo de recebimento).
export const FORMAS_PAGAMENTO = [
  { v: "", label: "—" },
  { v: "dinheiro", label: "Dinheiro" },
  { v: "pix", label: "Pix" },
  { v: "cartao", label: "Cartão" },
  { v: "transferencia", label: "Transferência" },
];

export const labelForma = (v) =>
  FORMAS_PAGAMENTO.find((f) => f.v === (v || ""))?.label || "—";

// Navegação de mês em "AAAA-MM", com virada de ano correta.
export function mesAnterior(mes) {
  const [a, m] = mes.split("-").map(Number);
  return m === 1 ? `${a - 1}-12` : `${a}-${String(m - 1).padStart(2, "0")}`;
}

export function mesSeguinte(mes) {
  const [a, m] = mes.split("-").map(Number);
  return m === 12 ? `${a + 1}-01` : `${a}-${String(m + 1).padStart(2, "0")}`;
}

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

// "2026-10" -> "Outubro/2026".
export function formatMesBR(mes) {
  const [a, m] = (mes || "").split("-");
  const nome = MESES[Number(m) - 1];
  return nome ? `${nome}/${a}` : mes || "—";
}

// Mês corrente "AAAA-MM" no fuso LOCAL (não UTC — a virada do mês no Brasil
// aconteceria 3h antes do previsto se usássemos toISOString aqui).
export const mesAtual = () => hojeISO().slice(0, 7);

// Validação de CPF pelos dígitos verificadores (mesma regra do backend).
export function isValidCpf(v) {
  const d = onlyDigits(v);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  for (let t = 9; t < 11; t++) {
    let soma = 0;
    for (let i = 0; i < t; i++) soma += parseInt(d[i], 10) * (t + 1 - i);
    let dig = (soma * 10) % 11;
    if (dig === 10) dig = 0;
    if (dig !== parseInt(d[t], 10)) return false;
  }
  return true;
}
