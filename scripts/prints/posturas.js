// Gera 4 imagens ilustrativas de avaliação postural (silhueta sobre grade de simetrógrafo),
// antes e depois, frente e lateral. Só para os prints do site.
const { chromium } = require("playwright-core");
const path = require("path");
const fs = require("fs");

const CHROME = path.join(process.env.LOCALAPPDATA,
  "ms-playwright/chromium-1234/chrome-win64/chrome.exe");
const OUT = path.join(__dirname, "out", "posturas");
fs.mkdirSync(OUT, { recursive: true });

const S = 800;
const corpo = "#3d352c", braco = "#5a5045", fio = "#c0563f";

function grade() {
  let g = `<rect width="${S}" height="${S}" fill="#f7f4ee"/>`;
  for (let i = 0; i <= S; i += 40) {
    const forte = i % 200 === 0;
    const c = forte ? "#cfc5b6" : "#e4ddd2", w = forte ? 2 : 1;
    g += `<line x1="${i}" y1="0" x2="${i}" y2="${S}" stroke="${c}" stroke-width="${w}"/>`;
    g += `<line x1="0" y1="${i}" x2="${S}" y2="${i}" stroke="${c}" stroke-width="${w}"/>`;
  }
  return g;
}

function rotulo(txt) {
  return `<rect x="24" y="${S - 76}" rx="22" width="${txt.length * 15 + 40}" height="48" fill="#26221d"/>
  <text x="44" y="${S - 44}" font-family="Segoe UI, sans-serif" font-size="24" font-weight="600"
    letter-spacing="2" fill="#f3ece1">${txt}</text>`;
}

const seg = (a, b, w, c = corpo) =>
  `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`;

function lateral(antes) {
  const ank = [400, 690], knee = [antes ? 408 : 404, 550], hip = [antes ? 392 : 398, 410];
  const sh = antes ? [422, 254] : [402, 248], ear = antes ? [452, 180] : [406, 168];
  const head = antes ? [462, 154] : [412, 138];
  const ctrl = antes ? [384, 328] : [394, 330];
  const hand = [sh[0] + (antes ? 22 : 6), sh[1] + 210];
  return `${grade()}
  ${seg([372, 716], [476, 716], 30)}
  ${seg(ank, knee, 66)}${seg(knee, hip, 78)}
  <path d="M${hip[0]} ${hip[1]} Q${ctrl[0]} ${ctrl[1]} ${sh[0]} ${sh[1]}" stroke="${corpo}" stroke-width="118" fill="none" stroke-linecap="round"/>
  ${seg(sh, ear, 50)}
  <circle cx="${head[0]}" cy="${head[1]}" r="54" fill="${corpo}"/>
  ${seg(sh, hand, 42, braco)}
  ${[ear, sh, hip, knee, ank].map((p) => `<circle cx="${p[0]}" cy="${p[1]}" r="9" fill="#e7c99b" stroke="#26221d" stroke-width="3"/>`).join("")}`;
}

function frente(antes) {
  const y1 = antes ? 246 : 258, y2 = antes ? 274 : 258, dx = antes ? -14 : 0;
  const l = [306, y1], r = [494, y2];
  return `${grade()}
  ${seg([356, 470], [350, 712], 66)}${seg([444, 470], [450, 712], 66)}
  <path d="M${l[0]} ${l[1]} L${r[0]} ${r[1]} L462 480 L338 480 Z" fill="${corpo}" stroke="${corpo}" stroke-width="40" stroke-linejoin="round"/>
  ${seg(l, [282, l[1] + 230], 42, braco)}${seg(r, [518, r[1] + 230], 42, braco)}
  ${seg([400 + dx / 2, 200], [400, 250], 50)}
  <circle cx="${400 + dx}" cy="140" r="56" fill="${corpo}"/>`;
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });
  const page = await browser.newPage({ viewport: { width: S, height: S } });
  const lista = [
    ["1-jan-lateral", lateral(true), "JAN · LATERAL"],
    ["2-jan-frente", frente(true), "JAN · FRENTE"],
    ["3-abr-lateral", lateral(false), "ABR · LATERAL"],
    ["4-abr-frente", frente(false), "ABR · FRENTE"],
  ];
  for (const [nome, svg, txt] of lista) {
    await page.setContent(`<body style="margin:0"><svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}">${svg}</svg></body>`);
    await page.screenshot({ path: path.join(OUT, `${nome}.jpg`), quality: 85 });
  }
  await browser.close();
  console.log("ok");
})();
