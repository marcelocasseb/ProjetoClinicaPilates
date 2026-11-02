// Tira prints do front local (backend com dados de exemplo). Login simulado: um JWT
// falso no localStorage — o backend local ignora o token.
const { chromium } = require("playwright-core");
const path = require("path");

const CHROME = path.join(process.env.LOCALAPPDATA,
  "ms-playwright/chromium-1234/chrome-win64/chrome.exe");
const OUT = path.join(__dirname, "out");
const URL = "http://localhost:5173";

// Próxima segunda-feira às 08:15 (hoje, se já for segunda): a mesma data de dev_vitrine.py.
function proximaSegunda() {
  const d = new Date();
  d.setDate(d.getDate() + ((8 - d.getDay()) % 7));
  d.setHours(8, 15, 0, 0);
  return d;
}

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const token = [b64({ alg: "none" }), b64({
  "custom:clinicId": "local", "custom:role": "admin",
  email: "juliana@studioequilibrio.com.br", name: "Juliana Costa",
  exp: Math.floor(Date.now() / 1000) + 30 * 86400,
}), "x"].join(".");
const sessao = JSON.stringify({ idToken: token, accessToken: token, refreshToken: "x",
  claims: JSON.parse(Buffer.from(token.split(".")[1], "base64url")) });

async function abrir(page, aba, sub) {
  await page.getByRole("button", { name: aba, exact: false }).first().click();
  if (sub) await page.getByRole("menuitem", { name: sub }).click();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });

  for (const [modo, viewport, escala] of [["desk", { width: 1366, height: 860 }, 1.25],
                                          ["mob", { width: 390, height: 844 }, 2]]) {
    // Login (sem sessão)
    const ctx0 = await browser.newContext({ viewport, deviceScaleFactor: escala, locale: "pt-BR" });
    const p0 = await ctx0.newPage();
    await p0.goto(URL); await p0.waitForTimeout(800);
    await p0.screenshot({ path: `${OUT}/${modo}-login.jpg`, quality: 80 });
    await ctx0.close();

    const ctx = await browser.newContext({ viewport, deviceScaleFactor: escala, locale: "pt-BR" });
    await ctx.addInitScript((s) => localStorage.setItem("auth", s), sessao);
    await ctx.clock.setFixedTime(proximaSegunda());
    const page = await ctx.newPage();
    await page.goto(URL);
    await page.waitForLoadState("networkidle"); await page.waitForTimeout(800);
    await page.screenshot({ path: `${OUT}/${modo}-inicio.jpg`, quality: 80 });

    const lista = [
      ["pacientes", "Pacientes"], ["agenda", "Agenda"],
      ["pilates", "Pilates", "Pilates"], ["escala", "Pilates", "Escala"],
      ["financeiro", "Financeiro"], ["aparelhos", "Parametrização", "Aparelhos"],
    ];
    for (const [nome, aba, sub] of lista) {
      try {
        await abrir(page, aba, sub);
        await page.screenshot({ path: `${OUT}/${modo}-${nome}.jpg`, quality: 80 });
      } catch (e) { console.log("falhou", modo, nome, e.message.split("\n")[0]); }
    }
    await ctx.close();
  }
  await browser.close();
  console.log("ok");
})();
