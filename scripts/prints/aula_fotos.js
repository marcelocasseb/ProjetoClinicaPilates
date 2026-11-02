// Prints da aula de Pilates sendo registrada e das fotos de evolução na ficha do aluno.
// Front com VITE_MOCK_IMAGENS=1 (upload simulado no navegador).
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

const FOTOS = ["1-jan-lateral", "2-jan-frente", "3-abr-lateral", "4-abr-frente"]
  .map((n) => path.join(__dirname, "out", "posturas", `${n}.jpg`));

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const token = [b64({ alg: "none" }), b64({
  "custom:clinicId": "local", "custom:role": "admin",
  email: "juliana@studioequilibrio.com.br", name: "Juliana Costa",
  exp: Math.floor(Date.now() / 1000) + 30 * 86400,
}), "x"].join(".");
const sessao = JSON.stringify({ idToken: token, accessToken: token, refreshToken: "x",
  claims: JSON.parse(Buffer.from(token.split(".")[1], "base64url")) });

const pausa = (p, ms = 500) => p.waitForTimeout(ms);

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });
  for (const [modo, viewport, escala] of [["desk", { width: 1366, height: 860 }, 1.25],
                                          ["mob", { width: 390, height: 844 }, 2]]) {
    const ctx = await browser.newContext({ viewport, deviceScaleFactor: escala, locale: "pt-BR" });
    await ctx.addInitScript((s) => localStorage.setItem("auth", s), sessao);
    await ctx.clock.setFixedTime(proximaSegunda());
    const page = await ctx.newPage();
    await page.goto(URL);
    await page.waitForLoadState("networkidle");

    // --- Aula de Pilates sendo registrada ---
    await page.getByRole("button", { name: "Pilates" }).first().click();
    await page.getByRole("menuitem", { name: "Pilates" }).click();
    await page.waitForLoadState("networkidle");
    await page.locator("tr.row-click", { hasText: "Beatriz Santos" }).click();
    await page.waitForLoadState("networkidle"); await pausa(page, 700);
    const selects = page.locator("main select");
    await selects.nth(0).selectOption({ label: "Dra. Ana Lima" });
    await selects.nth(1).selectOption({ label: "Reformer (Grande porte)" });
    await pausa(page, 300);
    for (const t of ["Footwork", "Alongamento", "Core"]) {
      await page.locator("button.chip", { hasText: t }).first().click();
    }
    await selects.nth(1).selectOption({ label: "Chair (Médio porte)" });
    await pausa(page, 300);
    await page.locator("button.chip", { hasText: "Fortalecimento" }).first().click();
    await selects.nth(1).selectOption({ label: "Cadillac (Grande porte)" });
    await pausa(page, 300);
    await page.locator("button.chip", { hasText: "Mobilidade" }).first().click();
    await page.locator("textarea.obs").fill(
      "Boa evolução na mobilidade da coluna. Sem dor lombar hoje. Próxima aula: progredir carga no Footwork.");
    await page.evaluate(() => window.scrollTo(0, 0)); await pausa(page);
    await page.screenshot({ path: `${OUT}/${modo}-aula.jpg`, quality: 80 });

    // --- Fotos de evolução na ficha do aluno ---
    await page.getByRole("button", { name: "Pacientes" }).first().click();
    await page.waitForLoadState("networkidle");
    await page.locator("tr.row-click", { hasText: "Beatriz Santos" }).click();
    await page.waitForLoadState("networkidle"); await pausa(page, 700);
    for (const f of FOTOS) {
      await page.locator('#secao-imagens input[type="file"]').setInputFiles(f);
      await pausa(page, 900);
    }
    const sec = page.locator("#secao-imagens");
    await sec.scrollIntoViewIfNeeded(); await pausa(page);
    await sec.screenshot({ path: `${OUT}/${modo}-fotos.jpg`, quality: 85 });
    await page.locator("#secao-avaliacoes").screenshot({ path: `${OUT}/${modo}-avaliacao-fotos.jpg`, quality: 80 });
    await ctx.close();
  }
  await browser.close();
  console.log("ok");
})();
