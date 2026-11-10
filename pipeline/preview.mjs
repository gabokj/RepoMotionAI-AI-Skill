#!/usr/bin/env node
/* Preview: renderiza só os quadros listados (PNG) para conferência rápida.
   Uso: node preview.mjs <pagina.html> <dir_frames> <quadros_csv> <total_quadros> [largura] [altura]
   Ex.: node preview.mjs cena.html prev "0,60,160,300" 840 1080 1920
   Abre a página num Chromium sem tela, chama renderFrame(n) para cada
   quadro e fotografa. Determinístico: mesmo input -> mesmos pixels. */
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

const [html, outDir, framesArg, totalArg, wArg, hArg] = process.argv.slice(2);
const FRAMES = (framesArg || "0,60,120,180").split(",").map(s => parseInt(s, 10)).filter(x => !isNaN(x));
const N = parseInt(totalArg || "480", 10);
const START = 0;
const VW = parseInt(wArg || "1080", 10), VH = parseInt(hArg || "1920", 10);
const PORT = parseInt(process.env.PORT || "9333", 10);
const FMT = process.env.FMT || "png";
mkdirSync(outDir, { recursive: true });

import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const HERE = dirname(fileURLToPath(import.meta.url));
const CHROME_CANDIDATES = [
  process.env.CHROME_BIN,
  join(HERE, "chrome-headless-shell/linux-157.0.8103.38/chrome-headless-shell-linux64/chrome-headless-shell"),
  "/home/hatch/workspace/motion-frames/chrome-headless-shell/linux-157.0.8103.38/chrome-headless-shell-linux64/chrome-headless-shell",
].filter(Boolean);
const CHROME = CHROME_CANDIDATES.find(c => existsSync(c)) || CHROME_CANDIDATES[0];
const chrome = spawn(CHROME, [
  "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
  `--remote-debugging-port=${PORT}`, `--window-size=${VW},${VH}`,
  "--force-device-scale-factor=1", "about:blank",
], { stdio: "ignore" });

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitVersion() {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) return await r.json(); } catch {}
    await sleep(250);
  }
  throw new Error("chromium nao respondeu");
}

let msgId = 0;
const pending = new Map();
let ws, sessionId = null;
function send(method, params = {}) {
  const id = ++msgId;
  const msg = { id, method, params };
  if (sessionId) msg.sessionId = sessionId;
  ws.send(JSON.stringify(msg));
  return new Promise((res, rej) => pending.set(id, { res, rej }));
}

const version = await waitVersion();
ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener("open", r, { once: true }));
ws.addEventListener("message", ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id); pending.delete(m.id);
    if (m.error) rej(new Error(m.error.message)); else res(m.result);
  }
});

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
({ sessionId } = await send("Target.attachToTarget", { targetId, flatten: true }));
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: VW, height: VH, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: "file://" + resolve(html) });
await sleep(600);
await send("Runtime.evaluate", { expression: "document.fonts.ready.then(()=>1)", awaitPromise: true });

const t0 = Date.now();
const EXT = FMT === "jpeg" ? "jpg" : "png";
for (const n of FRAMES) {
  await send("Runtime.evaluate", { expression: `window.renderFrame(${n})` });
  const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  writeFileSync(`${outDir}/f${String(n).padStart(4, "0")}.png`, Buffer.from(shot.data, "base64"));
  console.log(`frame ${n}/${N}  (${((Date.now()-t0)/1000).toFixed(1)}s)`);
}
console.log(`OK preview em ${((Date.now()-t0)/1000).toFixed(1)}s`);
ws.close(); chrome.kill();
process.exit(0);
